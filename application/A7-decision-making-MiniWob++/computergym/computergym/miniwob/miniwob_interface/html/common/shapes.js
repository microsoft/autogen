/*
Utilities for generating and describing shapes/digits/letters in a grid
that have various properties.
*/

var shapes = {};

// env variables
shapes.SZ_X = 7; // number of bins for shapes
shapes.SZ_Y = 7;
shapes.MAX_SIZE = 20; // max render size of shapes in pixels. Note by default grid is 160x160, so 8*20=160.

shapes.MAX_NUM_SHAPES = 20;
shapes.MIN_NUM_SHAPES = 3;
shapes.COLORS = ['red', 'green', 'blue', 'aqua', 'black', 'magenta', 'yellow'];
shapes.LETTERS = 'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM';
shapes.DIGITS = '1234567890';
shapes.SHAPES = ['circle', 'rectangle', 'triangle'];

// helper function that creates a grid of shapes
shapes.genGrid = function(n) {

  var grid = {};
  grid.shapes = [];

  var taken_positions = [];
  var num_shapes = typeof n !== 'undefined' ? n : core.randi(shapes.MIN_NUM_SHAPES, shapes.MAX_NUM_SHAPES);
  for(var i=0;i<num_shapes;i++) {

    // generate properties of a shape
    while(true) {
      var x = core.randi(0, shapes.SZ_X);
      var y = core.randi(0, shapes.SZ_Y);
      var xystr = x + ',' + y;
      if(!taken_positions.hasOwnProperty(xystr)) { // make sure it's not taken yet
        taken_positions[xystr] = 1;
        break;
      }
    }
    var color = shapes.COLORS[core.randi(0, shapes.COLORS.length)];
    var size = core.randf(0,1) < 0.5 ? 1 : 0;

    // a letter, digit or a shape
    var r = core.randf(0,1);
    if(r < 0.5) {
      var type = 'letter';
      var text = shapes.LETTERS[core.randi(0, shapes.LETTERS.length)];
    } else if(r < 0.7) {
      var type = 'digit';
      var text = shapes.DIGITS[core.randi(0, shapes.DIGITS.length)];
    } else {
      var type = 'shape';
      var text = shapes.SHAPES[core.randi(0, shapes.SHAPES.length)];
    }

    var shape = {x:x, y:y, color:color, size:size, type:type, text:text}
    grid.shapes.push(shape)
  }

  return grid;
}

// renders the grid into svg and modifies grid in place with pointers to the added elements.
shapes.renderGrid = function(svg, grid) {

  svg.html(''); // clear previous problem, if any
  grid.svg = svg; // save the element to grid object

  // // draw grid (used in debugging)
  // var drawGrid = function() {
  //   for(var x=0;x<shapes.SZ_X;x++) {
  //     for(var y=0;y<shapes.SZ_Y;y++) {
  //       var svg_shape = svg.append('circle')
  //         .attr('cx', x*shapes.MAX_SIZE + shapes.MAX_SIZE/2)
  //         .attr('cy', y*shapes.MAX_SIZE + shapes.MAX_SIZE/2)
  //         .attr('r', shapes.MAX_SIZE/2)
  //         .attr('fill', '#FFF')
  //         .attr('stroke', '#000');
  //     }
  //   }
  // }
  // drawGrid();

  var shapesToRender = grid.shapes;
  for(var i=0, n=shapesToRender.length; i<n; i++) {
    var s = shapesToRender[i]; // shape
    var xcoord = s.x*shapes.MAX_SIZE + shapes.MAX_SIZE/2; // of center
    var ycoord = s.y*shapes.MAX_SIZE + shapes.MAX_SIZE/2;
    var szcoord = Math.ceil(shapes.MAX_SIZE/2*s.size)+shapes.MAX_SIZE/2;

    if(s.type === 'letter' || s.type === 'digit') {
      var svg_shape = svg.append('text')
        .attr('x', xcoord)
        .attr('y', ycoord)
        .attr('fill', s.color)
        .attr('text-anchor', 'middle')
        .attr('alignment-baseline', 'central')
        .attr('font-size', szcoord + 'px')
        .text(s.text);
    }
    if(s.type === 'shape') {
      if(s.text === 'rectangle') {
        var svg_shape = svg.append('rect')
        .attr('x', xcoord-szcoord/2)
        .attr('y', ycoord-szcoord/2)
        .attr('width', szcoord)
        .attr('height', szcoord)
        .attr('fill', s.color);
      }
      if(s.text === 'circle') {
        var svg_shape = svg.append('circle')
          .attr('cx', xcoord)
          .attr('cy', ycoord)
          .attr('r', szcoord/2)
          .attr('fill', s.color);
      }
      if(s.text === 'triangle') {
        var points = (xcoord - szcoord/2) + ',' + (ycoord + szcoord/2) + ' '
                    +(xcoord) + ',' + (ycoord - szcoord/2) + ' '
                    +(xcoord + szcoord/2) + ',' + (ycoord + szcoord/2);
        var svg_shape = svg.append('polygon')
          .attr('points', points)
          .attr('fill', s.color);
      }
    }

    svg_shape.attr('style', 'cursor:pointer;'); // make hand pointer
    s.svg_shape = svg_shape; // modify grid in place, attach the actual SVG element to the dict
  }
}

shapes.generalDesc = function(s) {
  // given a shape, describe it in text in a lossy way (ignoring some attributes at random)
  var text = '';
  var sztxt = core.randf(0,1) < 0.5 ? ((s.size == 1 ? 'large' : 'small')) : '';
  if(sztxt !== '') { text += sztxt + ' '; }
  var coltxt = core.randf(0,1) < 0.5 ? s.color : '';
  if(coltxt !== '') { text += coltxt + ' '; }
  if(core.randf(0,1) < 0.5 || (sztxt === '' && coltxt === '')) {
    if(core.randf(0,1) < 0.5) {
      var stxt = s.text; // reveal full details
    } else {
      var stxt = s.type; // reveal only type (e.g. shape/digit/letter)
    }
  } else {
    var stxt = 'item'; // reveal nothing
  }
  text += stxt;
  return {text: text, parts:[sztxt, coltxt, stxt]};
}

shapes.sampleDesc = function() {
  // sample a random possible description
  var g = shapes.genGrid(1);
  var desc = shapes.generalDesc(g.shapes[0]);
  return desc;
}

shapes.shapeMatchesText = function(s, desc) {
  // verifies that a shape matches some description
  var szmatch = desc.parts[0] === '' || ((s.size == 1 ? 'large' : 'small') === desc.parts[0]);
  var colmatch = desc.parts[1] === '' || (s.color === desc.parts[1]);
  var smatch = desc.parts[2] === 'item' || (s.text === desc.parts[2] || s.type === desc.parts[2]); // fine for now. technically we're mixing up type/text
  return szmatch && colmatch && smatch;
}

// function to define dragging a shape around a grid
shapes.drag = d3.behavior.drag()
  .on('drag', function(){
    var dim = this.getBBox().width;
    var shapeType = this.tagName;
    var shift_x = d3.event.x - this.getBBox().x;
    var shift_y = d3.event.y - this.getBBox().y;

    if(shapeType==='rect') {
      shift_x -= dim*0.5;
      shift_y -= dim*0.5;
    } else if(shapeType==='circle') {
      shift_x -= dim*0.6;
      shift_y -= dim*0.6;
    } else if(shapeType==='polygon') {
      shift_x -= dim*0.4;
      shift_y -=  dim*0.4;
    }

    d3.select(this)
      .attr("transform", "translate(" + shift_x + "," + shift_y + ")");
});

// determine coordinates of a shape within a grid
shapes.gridCoords = function(shape){
  var shapeType = shape.tagName;
  var coords = {};
  coords.x = shape.getBBox().x;
  coords.y = shape.getBBox().y;

  if(shape.getAttribute('transform') === null) return coords;
  else var shift = shape.getAttribute('transform').replace(/[^0-9\,\-\.]+/g, '').split(",")

  coords.x += parseFloat(shift[0],10);
  coords.y += parseFloat(shift[1],10);

  return coords;
}

// draw circles on a given grid.
shapes.drawCircles = function(circles, grid){
  for(var i=0;i<circles.length;i++){
    var circle = circles[i];
    grid
      .append('circle')
      .attr('class', circle.class)
      .attr('id', circle.id)
      .attr('cx', circle.cx)
      .attr('cy', circle.cy)
      .attr('r', circle.r)
      .attr('stroke', circle.stroke ? circle.stroke : '')
      .attr('fill', circle.fill ? circle.fill : 'black');
  }
}

// draw lines on a given grid.
shapes.drawLines = function(lines, grid){
  for(var i=0;i<lines.length;i++){
    var line = lines[i];
    grid.append('line')
      .style('stroke', line.stroke ? line.stroke : 'black')
      .attr('class', line.class)
      .attr('x1', line.x1)
      .attr('x2', line.x2)
      .attr('y1', line.y1)
      .attr('y2', line.y2)
  }
}

