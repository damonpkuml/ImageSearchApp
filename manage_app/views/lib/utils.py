# coding:utf-8

from flask import render_template, abort, g, redirect, url_for, request, jsonify, session
from lib.paginator import SQLAlchemyPaginator
from model.session import get_session

from model.image.image_series import ImageSeries
from model.website.column import WebsiteColumnSeriesRel

from route import lib


@lib.route('/get_all_series', methods=['GET'])
def get_all_series():
    result = {
        'response': 'ok',
        'meta': '',
        'data_list': []
    }
    search = request.args.get('search')
    limit = request.args.get('limit', 10)
    page = request.args.get('page', 1)
    with get_session() as db_session:
        query = db_session.query(ImageSeries).order_by(-ImageSeries.modified_date)

        if search:
            query = query.filter(
                ImageSeries.name.like('%%%s%%' % search)
            )

        paginator = SQLAlchemyPaginator(query, limit)
        page = paginator.get_validate_page(page)

        _data_list = list()

        for series in paginator.page(page):
            series_dict = series.to_dict()
            _data_list.append(series_dict)

        result['data_list'] = _data_list
        result.update({
            'meta': {
                'cur_page': page,
                'all_page': paginator.max_page,
                'count': paginator.count
            }
        })
    return jsonify(result)


# 主要用于栏目中防止专题的重复选择
@lib.route('/get_column_all_series', methods=['GET'])
def get_column_all_series():
    result = {
        'response': 'ok',
        'meta': '',
        'data_list': []
    }
    search = request.args.get('search')
    limit = request.args.get('limit', 10)
    page = request.args.get('page', 1)
    column_id = request.args.get('column_id')
    with get_session() as db_session:
        query = db_session.query(ImageSeries).order_by(-ImageSeries.modified_date)

        has_series_list = list()
        all_series = db_session.query(WebsiteColumnSeriesRel).filter(
            WebsiteColumnSeriesRel.column_id == column_id
        ).all()
        for series in all_series:
            has_series_list.append(series.series_id)
        query = query.filter(
            ImageSeries.id.notin_(has_series_list)
        )

        if search:
            query = query.filter(
                ImageSeries.name.like('%%%s%%' % search)
            )

        paginator = SQLAlchemyPaginator(query, limit)
        page = paginator.get_validate_page(page)

        _data_list = list()

        for series in paginator.page(page):
            series_dict = series.to_dict()
            _data_list.append(series_dict)

        result['data_list'] = _data_list
        result.update({
            'meta': {
                'cur_page': page,
                'all_page': paginator.max_page,
                'count': paginator.count
            }
        })
    return jsonify(result)