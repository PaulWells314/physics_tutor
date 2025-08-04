function create_draw_pic(ctx, pic_width, pic_height) {
   function draw_pic(){
      slope_degrees = 30;
      ctx.save();
      ctx.beginPath();
      ctx.translate(0.5 + pic_width/2, 0.5 + pic_height/2);
      ctx.rotate(-slope_degrees*Math.PI/180);
      ctx.rect(-0.1*pic_width, -0.1*pic_width, 0.2*pic_width, 0.2*pic_width);
      ctx.fillStyle = "blue";
      ctx.fill();
      ctx.moveTo(-0.4*pic_width, 0.1*pic_width);
      ctx.lineTo(0.4*pic_width, 0.1*pic_width);
      ctx.stroke();
      ctx.restore();
  }
  return draw_pic;
}
