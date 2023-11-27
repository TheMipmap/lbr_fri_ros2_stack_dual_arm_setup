/** palm_with_finger_cutouts.scad - simple OpenSCAD model with 
 * cavtities around the finger mount positions, so that Gazebo can 
 * simulate without permanent self-collisions. Export as STL, then 
 * use as collision mesh for your robot model.
 *
 * (c) 2023 fnh, hendrich@informatik.uni-hamburg.de
 */


// a sphere, just for initial alignment of stuff...
// sphere( d=0.12, $fn=100 );

difference() {
  color( "green", 0.5 )
    import( "palm.STL" );

  // from Robotiq datasheet: finger width at base is 30.75 mm,
  // so a cutout of dy=40.00 mm width should be fine.

  for( sign=[-1,+1] )
    translate( [-0.04, 0.028, sign*0.033] )
      cube( [0.06, 0.05, 0.05], center=true );
  
  translate( [0.04, 0.028, 0.0] )
    cube( [0.06, 0.05, 0.04], center=true );
}  