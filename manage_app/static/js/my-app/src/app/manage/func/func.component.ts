declare var $: any;

import { Component, OnInit, OnChanges, Input} from '@angular/core';
import { ActivatedRoute, Params, Router }   from '@angular/router';
import { Location }  from '@angular/common';

import { ListBaseComponent } from '../../common/base.component';
import { Func } from '../../model/func';
import { FuncService } from './func.service';

@Component({
  selector: 'func-root',
  templateUrl: './func_list.html',
})
export class FuncConfComponent extends ListBaseComponent{
	func_list: Func[];
	
	constructor(private service: FuncService) {
		super();
	}
	
	getPagerData(): void {
		this.isLoading = true;
		this.service.getFuncs().then(data => {
        	this.func_list = data.func_list;
        });
		this.isLoading = false;
	}

}

@Component({
  selector: 'func-detail-root',
  templateUrl: './func_detail.html',
})
export class FuncConfDetailComponent{
}