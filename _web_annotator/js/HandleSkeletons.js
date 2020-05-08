//
//
//
//
//
import { APP } from "./APP";
import { parseCSV, csvFormatter } from "./csv";


// Change the opacity of all surface objects

APP.addSkeletons = function() {
	APP.scene.traverse(function(obj) {
		if ( (obj instanceof THREE.Mesh === true) && (obj.name.length === 10) ) {
			var id  = obj.name - 0;
			var col = obj.material.color;
			APP.addSkeletonObject(id, col)
		}
	});
}

APP.removeSkeletons = function() {
	APP.scene.traverse(function(obj) {
		if ( obj.name.match(/line/) ) {
			APP.scene.remove(obj);
		}
	});
}


// Add stl objects and a name
APP.addSkeletonObject = function(id, col) {

	if (APP.SkeletonMode == 0){
		return false;
		}

	const target_url = location.protocol+"//"+location.host+"/skeleton/whole/" + ( '0000000000' + id ).slice( -10 ) + ".hdf5";
	const filename   = ( '0000000000' + id ).slice( -10 ) + ".hdf5";
	fetch(target_url)
	  .then(function(response) {
	    return response.arrayBuffer() 
	  })
	  .then(function(buffer) {
	    //
	    //
	    var f = new hdf5.File(buffer, filename);
	    let g1 = f.get('vertices');
	    let g2 = f.get('edges');
	    var data_vertices = g1.value;
	    var data_edges    = g2.value;
	    
	    data_vertices = splitArray(data_vertices, 3);
	    data_edges    = splitArray(data_edges, 2);
	    
	    
		var i1 = undefined;
		var i2 = undefined;
		var v1 = undefined;
		var v2 = undefined;
		// console.log(data_vertices)
		console.log('Length vertices: ' + data_vertices.length);
		console.log('Length edges   : ' + data_edges.length);
		if (isNaN(data_vertices[0][0]) == true) {
			// console.log(data_vertices);
			console.log('No morphological data.');
			return false;
		}

		var geometry = new THREE.Geometry();
		var material = new THREE.LineBasicMaterial({
			color: col,  //0x000000
			linewidth: 3,
			fog:true
		});
		
		
		var scale_factor_xy = 5;
		var xscale = 1.0 / Math.pow(2, scale_factor_xy);
		var yscale = 1.0 / Math.pow(2, scale_factor_xy);
		var zscale = 1.0 / 40;

		
		for(var i=0;i< data_edges.length;i++){
			i1 = data_edges[i][0];
			i2 = data_edges[i][1];

			// console.log('Vertices ID: ', i1, i2 );

			v1 = new THREE.Vector3( data_vertices[i1][0]*zscale, data_vertices[i1][2]*yscale, data_vertices[i1][1]*xscale);
			v2 = new THREE.Vector3( data_vertices[i2][0]*zscale, data_vertices[i2][2]*yscale, data_vertices[i2][1]*xscale);
			geometry.vertices.push(v1, v2);
			}
		var line = new THREE.LineSegments( geometry, material );   
		
		
		line.name = 'line' + ( '0000000000' + id ).slice( -10 );
		console.log(line.name);
		APP.scene.add( line );	    
	    //
	    //
	    //
	  });
	}


// Change the color of a skeleton object specified by a name.
APP.changeSkeletonObjectColor = function(id, col) {
	name = 'line' + ( '0000000000' + id ).slice( -10 );
	var obj = APP.scene.getObjectByName(name_centerline);
	if ( obj != undefined ) {
		obj.material.color.setHex( col );
		}
	}


// Remove a stl object by the name.
APP.removeSkeletonObject = function(id) {
	name = 'line' + ( '0000000000' + id ).slice( -10 );
	var obj = APP.scene.getObjectByName(name);
	if ( obj != undefined ) {
		APP.scene.remove(obj);
		}
	}


function splitArray(array, part) {
    var tmp = [];
    for(var i = 0; i < array.length; i += part) {
        tmp.push(array.slice(i, i + part));
    }
    return tmp;
}





