import { Component, Input, Output, EventEmitter } from '@angular/core';

require('./waterfall.js');

declare var $: any;

@Component({
    selector: 'image-list',
	templateUrl: './image_list.html'
})
export class ImageQueryComponent {
	const url = '127.0.0.1:8888/manage/iamge_list'
	
	constructor() {};
	
	ngOnInit(): void { 
		// 流体式布局
		console.log($.fn);
		$("#demo").waterfall({
			itemClass: ".box",
			minColCount: 2,
			spacingHeight: 10,
			resizeable: true,
			ajaxCallback: function(success, end) {
				var data = {"data": [
					{ "src": "03.jpg" }, { "src": "04.jpg" }, { "src": "02.jpg" }, { "src": "05.jpg" }, { "src": "01.jpg" }, { "src": "06.jpg" }
				]};
				var str = "";
				var templ = '<div class="box" style="opacity:0;filter:alpha(opacity=0);"><div class="pic"><img src="/static/{{src}}" /></div></div>'

				for(var i = 0; i < data.data.length; i++) {
					str += templ.replace("{{src}}", data.data[i].src);
				}
				$(str).appendTo($("#div1"));
				success();
				end();
			}
		});
	}
}