import socket
import sys, os, time, errno
import tornado
import tornado.websocket
import tornado.httpserver
import asyncio
import h5py

import numpy as np
import json
import socketio

from marching_cubes import march
from stl import mesh

from os import path, pardir
main_dir = path.abspath(path.dirname(sys.argv[0]))  # Dir of main
sys.path.append(main_dir)
sys.path.append(path.join(main_dir, "system"))
sys.path.append(path.join(main_dir, "dojoio"))

from Params import Params
from DB import DB
from annotator.Annotator.sio import sio
import miscellaneous.Miscellaneous as m



class SurfaceHandler(tornado.web.RequestHandler):
  ###
  def __init__(self, *args, **kwargs):
    self.small_ids    = kwargs.pop('3Dmap')
    self.surfaces_whole_path = kwargs.pop('path')
    super(SurfaceHandler, self).__init__(*args, **kwargs)
  ###
  def get(self):
    id = self.get_argument('id', 'null')
    id = int(id)
    print('Target object id:', id)
    result = self.GenerateStl(id)
    if result :
        self.write("True")
    else :
        self.write("False")
  ###
  def GenerateStl(self, id):
    mask = (self.small_ids == id)
    # print('self.small_ids: ', self.small_ids)
    try:
        vertices, normals, faces = march(mask, 2)
    except:
        print('Mesh was not generated.')
        return False
    print('Generated face number: ', faces.shape)
    our_mesh = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
    for i, f in enumerate(faces):
        for j in range(3):
            our_mesh.vectors[i][j] = vertices[f[j], :]
    ###
    our_mesh.save(os.path.join(self.surfaces_whole_path, str(id).zfill(10)+'.stl' ))
    return True
  ###

  

class SkeletonHandler(tornado.web.RequestHandler):
  ###
  def __init__(self, *args, **kwargs):
    self.data_skeleton_path = kwargs.pop('path')
    super(SkeletonHandler, self).__init__(*args, **kwargs)
  ###
  def get(self):
    variable = self.get_argument('variable', 'null')
    id   = self.get_argument('id', 'null')
    print(id)
    if id == 'undefined':
      print('ID is undefined.')
      raise tornado.web.HTTPError(403)
      return False
    filename = os.path.join(self.data_skeleton_path, str(id).zfill(10)+'.hdf5')
    if os.path.isfile(filename) == False:
      print('No file exist: ', filename)
      raise tornado.web.HTTPError(403)
      return False
    print(filename)
    with h5py.File( filename ,'r') as f:
      if variable == 'edges':
          print('Send edges.')
          att = 'attachement; filename=edges.csv'
          target = f['edges'].value
      elif variable == 'vertices':
          print('Send vertices.')
          att = 'attachement; filename=vertices.csv'
          target = f['vertices'].value

          scale_factor_xy = 5
          xscale = 1 / (2 ** scale_factor_xy)
          yscale = 1 / (2 ** scale_factor_xy)
          zscale = 1 / 40
          #print('target[:,0].shape : ', target[:,0].shape)
          #print('target.shape : ', target.shape)
          #print('xscale : ', xscale)
          target = target[:,[0,2,1]]
          target[:,0] = target[:,0]*zscale
          target[:,1] = target[:,1]*xscale # Z
          target[:,2] = target[:,2]*yscale
          
          #
          
      else:
          print('No key.')
          raise tornado.web.HTTPError(403)
          return  False

    self.set_header('Content-Type','text/csv')
    self.set_header('content-Disposition', att)
    for targ in target:
      csv_data = ','.join(str(d) for d in targ) +'\n'
      # print(csv_data)
      self.write(csv_data) # mock data



class AnnotatorHandler(tornado.web.RequestHandler):
  def get(self):
    self.render('index.html')

class AnnotatorServerLogic:
  def __init__( self, u_info  ):
    ## User info
    self.u_info = u_info
    ## Load DB
    db = DB(self.u_info)

    ## Create 3D geometry

    scale_factor_xy = 2

    xmax = db.canvas_size_y / (2 ** scale_factor_xy)
    ymax = db.canvas_size_x / (2 ** scale_factor_xy)
    zmax = db.num_tiles_z
    cube_size = max([xmax, ymax, zmax])
    cube_size = np.ceil(cube_size)
    cube_size = cube_size.astype(np.int32)
    self.small_ids = np.zeros([cube_size, cube_size, cube_size], dtype=self.u_info.ids_dtype)

    for iz in range(db.num_tiles_z):
      full_map = m.ObtainFullSizeIdsPanel(self.u_info, db, iz)
      small_map = full_map[::(2 ** scale_factor_xy), ::(2 ** scale_factor_xy)]
      self.small_ids[0:small_map.shape[0], 0:small_map.shape[1], iz] = small_map

    boundingbox_dict = {'x': xmax, 'y': ymax, 'z': zmax}
    with open(os.path.join(self.u_info.surfaces_path, 'Boundingbox.json'), 'w') as f:
      json.dump(boundingbox_dict, f, indent=2, ensure_ascii=False)

    return None


  def rangeexpand(self, txt):
      lst = []
      for r in txt.split(','):
          if '-' in r[1:]:
              r0, r1 = r[1:].split('-', 1)
              lst += range(int(r[0] + r0), int(r1) + 1)
          else:
              lst.append(int(r))
      return lst


  def run( self ):
    ####
    web_path = os.path.join(self.u_info.web_annotator_path, "dist")
    css_path = os.path.join(self.u_info.web_annotator_path, "css")
    js_path  = os.path.join(self.u_info.web_annotator_path, "js")
    skeletons_path  = self.u_info.skeletons_path
    surfaces_path   = self.u_info.surfaces_path
    skeletons_whole_path = self.u_info.skeletons_whole_path
    surfaces_whole_path  = self.u_info.surfaces_whole_path
    ####
    # asyncio.set_event_loop(self.u_info.worker_loop_stl)
    ev_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ev_loop)

    annotator = tornado.web.Application([
      (r'/css/(.*)', tornado.web.StaticFileHandler, {'path': css_path}),
      (r'/js/(.*)', tornado.web.StaticFileHandler, {'path': js_path}),
      (r'/surface/(.*)', tornado.web.StaticFileHandler, {'path': surfaces_path}),
      (r'/surface/whole/(.*)', tornado.web.StaticFileHandler, {'path': surfaces_whole_path}),
      (r'/skeleton/(.*)', tornado.web.StaticFileHandler, {'path': skeletons_path}),
      (r'/ws/surface', SurfaceHandler, {'3Dmap': self.small_ids, 'path': surfaces_whole_path}),
      (r'/socket.io/', socketio.get_tornado_handler(sio)),
      (r'/(.*)', tornado.web.StaticFileHandler, {'path': web_path})
    ],debug=True,autoreload=True)


    server = tornado.httpserver.HTTPServer(annotator)
    server.listen(self.u_info.port_stl)
    print('*'*80)
    print('*', '3D Annotator RUNNING')
    print('*')
    print('*', 'open', '[ http://' + self.u_info.ip + ':' + str(self.u_info.port_stl) + '/] ')
    print('*'*80)

    tornado.ioloop.IOLoop.instance().start()
    #ev_loop.stop()
    #ev_loop.close()
    #server.stop()
    print("Tornado web server stops.")
    return


  def stop():
    print("Called stop")
    asyncio.asyncio_loop.stop()
    server.stop()


  def close(self, signal, frame):
    print('Sayonara..!!')
    sys.exit(0)

