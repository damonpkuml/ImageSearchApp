declare var $: any;
import { Injectable } from '@angular/core';
import { Headers, Http, Response, RequestOptions, RequestMethod } from '@angular/http';
import 'rxjs/add/operator/toPromise';
import 'rxjs/add/operator/timeout';
import 'rxjs/Rx';

import { BaseService } from '../../../common/base.service';

@Injectable()
export class UserChangePasswordService extends BaseService {
	
	constructor(http: Http) { 
		super(http);
	}
	
	getDetail(): Promise<any> {
		const url = '/auth_user_page';
		let self = this;
		return this.http.get(url).toPromise().then(function(res){
			let json = res.json();
			return json;
		});
	}

	changePassword(params: any): Promise<any> {
		const url = '/user_change_password';
		let res = this.postForm(url, JSON.stringify(params));
		return res;
	}
}