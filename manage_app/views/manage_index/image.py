# coding:utf-8

import traceback
import time
import datetime
import os
from PIL import Image
from flask import render_template, abort, g, redirect, url_for, request, jsonify, session
from flask.ext.login import current_user, login_user, logout_user, login_required
from flask import current_app as app
from sqlalchemy import or_, func, and_
from lib.upload_image import save_images, delete_images
from lib.paginator import SQLAlchemyPaginator
from model.base import IdGenerator
from model.session import get_session
from model.image.image import Image as Img
from model.image.image_series import ImageSeriesRel, ImageSeries, ImageSeriesCategory, ImageSeriesCategoryRel
from model.image.image_tags import ImageTags, ImageTagsRel, ImageRecommendTagsRel, ImageRecommendTags, ImageAssociationTag

from route import manage


# ———————————————————— 上传图片 ————————————————————
@manage.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    result = {
        'response': 'ok',
        'info': ''
    }
    file_objects = request.files.getlist('uploadedfile')
    series_ids = request.args.get('series_ids', '')
    _series_ids = series_ids.split(u',')
    tag_ids = request.args.get('tag_ids', '')
    _tag_ids = tag_ids.split(u',')
    try:
        if None in [file_objects]:
            result.update({
                'response': 'fail',
                'info': u'请上传图片'
            })
        else:
            save_images(file_objects, series_ids=_series_ids, tag_ids=_tag_ids)
        return jsonify(result)
    except Exception as e:
        print e
        abort(400)


# ———————————————————— 专题信息 ————————————————————
@manage.route('/image_info', methods=['GET'])
def image_info():
    result = {
        'response': 'ok',
        'image_series_list': [],
        'image_tag_list': []
    }
    try:
        with get_session() as db_session:
            all_image_series = db_session.query(ImageSeries).all()
            _image_series_list = list()
            for image_series in all_image_series:
                image_series_dict = image_series.to_dict()
                _image_series_list.append(image_series_dict)
            result['image_series_list'] = _image_series_list

            all_image_tag = db_session.query(ImageTags).all()
            _image_tag_list = list()
            for image_tag in all_image_tag:
                image_tag_dict = image_tag.to_dict()
                _image_tag_list.append(image_tag_dict)
            result['image_tag_list'] = _image_tag_list

        return jsonify(result)
    except Exception as e:
        print e
        abort(400)


# ———————————————————— 图片列表相关操作 ————————————————————
@manage.route('/image_list', methods=['GET'])
def image_list():
    result = {
        'response': 'ok',
        'image_list': [],
        'meta': {}
    }
    limit = 40
    page = request.args.get('page', 1)
    start_date = request.args.get('startDate', None)
    end_date = request.args.get('endDate', None)
    try:
        with get_session() as db_session:
            query = db_session.query(Img)

            if start_date and end_date:
                _start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
                _end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(
                    Img.created_date >= _start_date,
                    Img.created_date <= _end_date
                )

            query = query.order_by(-Img.created_date)

            paginator = SQLAlchemyPaginator(query, limit)
            page = paginator.get_validate_page(page)

            _img_list = list()
            for img in paginator.page(page):
                img_dict = img.to_dict()
                img_series_obj = db_session.query(ImageSeriesRel).filter(
                    ImageSeriesRel.image_id == img.id
                ).all()
                img_series_name = [image_series.image_series_name for image_series in img_series_obj]
                img_dict['image_series'] = img_series_name if img_series_name else [u'无']
                image_tag_obj = db_session.query(ImageTagsRel).filter(
                    ImageTagsRel.image_id == img.id
                ).all()
                img_tag_name = [image_tag.tag_name for image_tag in image_tag_obj]
                img_dict['image_tag'] = img_tag_name if img_tag_name else [u'无']
                _img_list.append(img_dict)

            result.update({
                'image_list': _img_list
            })

            result.update({
                'meta': {
                    'cur_page': page,
                    'all_page': paginator.max_page,
                    'count': paginator.count
                }
            })

            return jsonify(result)
    except Exception as e:
        print e
        abort(400)


# 删除图片
@manage.route('/image_list/delete', methods=['POST'])
def delete_image_list():
    result = {
        'response': 'ok',
        'info': ''
    }
    ids = request.form.get('ids').split(',')
    try:
        if ids[0]:
            # 删除记录的同时，删除本地文件
            delete_images(ids=ids)
        else:
            result.update({
                'response': 'fail',
                'info': u'当前未选择任何图片'
            })
        return jsonify(result)
    except Exception as e:
        app.my_logger.error(traceback.format_exc(e))
        abort(400)


# 设置专题封面
@manage.route('/set_image_cover', methods=['POST'])
def set_image_cover():
    result = {
        'response': 'ok',
        'info': ''
    }
    image_id = request.form.get('image_id').split(',')
    series_id = request.form.get('series_id')
    try:
        if len(image_id) == 1 and image_id[0] != u'':
            image_id = image_id[0]
            with get_session() as db_session:
                image_series = db_session.query(ImageSeries).get(series_id)
                if image_series:
                    image_series.cover_image_id = image_id
                    db_session.commit()
                else:
                    result.update({
                        'response': 'fail',
                        'info': u'当前选择的专题不存在'
                    })
        else:
            result.update({
                'response': 'fail',
                'info': u'设置专题封面只能选择一张图片'
            })
        return jsonify(result)
    except Exception as e:
        app.my_logger.error(traceback.format_exc(e))
        abort(400)


# 将图片添加至专题
@manage.route('/add_image_to_series', methods=['POST'])
def add_image_to_series():
    result = {
        'response': 'ok',
        'info': ''
    }
    image_ids = request.form.get('image_id', u'').split(',')
    series_id = request.form.get('series_id')
    try:
        if len(image_ids) > 0 and image_ids[0] != u'':
            with get_session() as db_session:
                image_series = db_session.query(ImageSeries).get(series_id)
                if image_series:
                    all_image = db_session.query(ImageSeriesRel).filter(
                        ImageSeriesRel.image_series_id == series_id
                    ).all()
                    all_image_ids = [str(image.image_id) for image in all_image]
                    add_image_ids = set(image_ids) - set(all_image_ids)
                    for image_id in add_image_ids:
                        image_series_rel = ImageSeriesRel()
                        image_series_rel.image_id = image_id
                        image_series_rel.image_series_id = series_id
                        image_series_rel.image_series_name = image_series.name
                        db_session.add(image_series_rel)
                    db_session.commit()
                else:
                    result.update({
                        'response': 'fail',
                        'info': u'当前选择的专题不存在'
                    })
        else:
            result.update({
                'response': 'fail',
                'info': u'请选择图片'
            })
        return jsonify(result)
    except Exception as e:
        app.my_logger.error(traceback.format_exc(e))
        abort(400)


# 将图片添加至标签
@manage.route('/add_image_to_tag', methods=['POST'])
def add_image_to_tag():
    result = {
        'response': 'ok',
        'info': ''
    }
    image_ids = request.form.get('image_id', u'').split(',')
    tag_id = request.form.get('tag_id')
    try:
        if len(image_ids) > 0 and image_ids[0] != u'':
            with get_session() as db_session:
                image_tag = db_session.query(ImageTags).get(tag_id)
                if image_tag:
                    all_image = db_session.query(ImageTagsRel).filter(
                        ImageTagsRel.tag_id == tag_id
                    ).all()
                    all_image_ids = [str(image.image_id) for image in all_image]
                    add_image_ids = set(image_ids) - set(all_image_ids)
                    for image_id in add_image_ids:
                        image_tag_rel = ImageTagsRel()
                        image_tag_rel.tag_id = tag_id
                        image_tag_rel.image_id = image_id
                        image_tag_rel.tag_name = image_tag.name
                        image_tag_rel.type = ImageTagsRel.TYPE_IMAGE
                        db_session.add(image_tag_rel)
                    db_session.commit()
                else:
                    result.update({
                        'response': 'fail',
                        'info': u'当前选择的标签不存在'
                    })
        else:
            result.update({
                'response': 'fail',
                'info': u'请选择图片'
            })
        return jsonify(result)
    except Exception as e:
        app.my_logger.error(traceback.format_exc(e))
        abort(400)


# ———————————————————— 图片专题相关操作 ————————————————————
@manage.route('/image_series_list', methods=['GET'])
def image_series_list():
    result = {
        'response': 'ok',
        'image_series_list': [],
        'info': ''
    }
    try:
        with get_session() as db_session:
            all_image_series = db_session.query(ImageSeries).all()
            _image_series_list = list()
            for image_series in all_image_series:
                image_series_dict = image_series.to_dict()
                _image_series_list.append(image_series_dict)
            result['image_series_list'] = _image_series_list
        return jsonify(result)
    except Exception as e:
        print e
        abort(400)


# 专题详情
@manage.route('/image_series_list/detail', methods=['GET'])
def get_image_series_detail():
    result = {
        'response': 'ok',
        'info': '',
        'image_series': ''
    }
    try:
        _id = request.args.get('id')
        with get_session() as db_session:
            image_series = db_session.query(ImageSeries).get(_id)
            if image_series:
                image_series_dict = image_series.to_dict()
                result['image_series'] = image_series_dict
            else:
                result.update({
                    'response': 'fail',
                    'info': u'当前系列不存在'
                })
        return jsonify(result)
    except Exception as e:
        app.my_logger.error(traceback.format_exc(e))
        abort(400)


# 更新专题
@manage.route('/image_series_list/update', methods=['POST'])
def update_image_series_detail():
    result = {
        'response': 'ok',
        'info': ''
    }
    image_series_id = request.form.get('id')
    image_series_name = request.form.get('name')
    image_series_desc = request.form.get('desc')
    image_series_short_desc = request.form.get('short_desc')
    image_series_type = request.form.get('type')
    try:
        if None in [image_series_name]:
            result.update({
                'response': 'fail',
                'info': u'请检查参数是否填写完整'
            })
        else:
            with get_session() as db_session:
                if not image_series_id:
                    image_series = ImageSeries()
                    image_series.name = image_series_name
                    image_series.desc = image_series_desc
                    image_series.short_desc = image_series_short_desc
                    image_series.author = current_user.name
                    image_series.type = image_series_type
                    db_session.add(image_series)
                else:
                    image_series = db_session.query(ImageSeries).get(image_series_id)
                    if image_series:
                        image_series.name = image_series_name
                        image_series.desc = image_series_desc
                        image_series.short_desc = image_series_short_desc
                        image_series.type = image_series_type
                    else:
                        result['response'] = 'fail'
                        result['info'] = u'当前对象不存在'
                db_session.commit()
        return jsonify(result)
    except Exception as e:
        app.my_logger.error(traceback.format_exc(e))
        abort(400)


# 删除专题
@manage.route('/image_series_list/delete', methods=['POST'])
def delete_image_series():
    result = {
        'response': 'ok',
        'info': ''
    }
    ids = request.form.get('ids').split(',')
    try:
        # 删除专题时，会将该专题中所有的专题与图片关系删除
        with get_session() as db_session:
            for _id in ids:
                image_series = db_session.query(ImageSeries).get(_id)
                if image_series:
                    # 删除专题
                    db_session.delete(image_series)

                    # 删除关系
                    db_session.query(ImageSeriesRel).filter(
                        ImageSeriesRel.image_series_id == _id
                    ).delete(synchronize_session=False)
            db_session.commit()
        return jsonify(result)
    except Exception as e:
        print e
        abort(400)


# 专题图片
@manage.route('/image_series_list/series_image_list', methods=['GET'])
def series_image_list():
    result = {
        'response': 'ok',
        'image_list': [],
        'meta': {}
    }
    limit = 40
    page = request.args.get('page', 1)
    series_id = request.args.get('series_id')
    try:
        with get_session() as db_session:
            query = db_session.query(Img).join(
                ImageSeriesRel, Img.id == ImageSeriesRel.image_id
            ).filter(
                ImageSeriesRel.image_series_id == series_id
            )

            image_series = db_session.query(ImageSeries).get(series_id)
            if image_series:
                paginator = SQLAlchemyPaginator(query, limit)
                page = paginator.get_validate_page(page)

                _img_list = list()
                for img in paginator.page(page):
                    img_dict = img.to_dict()
                    img_dict['image_series'] = [image_series.name]
                    image_tag_obj = db_session.query(ImageTagsRel).filter(
                        ImageTagsRel.image_id == img.id
                    ).all()
                    img_tag_name = [image_tag.tag_name for image_tag in image_tag_obj]
                    img_dict['image_tag'] = img_tag_name if img_tag_name else [u'无']
                    _img_list.append(img_dict)

                result.update({
                    'image_list': _img_list
                })

                result.update({
                    'meta': {
                        'cur_page': page,
                        'all_page': paginator.max_page,
                        'count': paginator.count
                    }
                })
            else:
                result['response'] = 'fail'
                result['info'] = u'当前专题不存在'
            return jsonify(result)
    except Exception as e:
        print e
        abort(400)


# 将图片移除专题
@manage.route('/image_series_list/remove_image_from_series', methods=['POST'])
def remove_image_from_series():
    result = {
        'response': 'ok',
        'info': ''
    }
    try:
        image_ids = request.form.get('image_id', u'').split(',')
        series_id = request.form.get('series_id')
        if len(image_ids) > 0 and image_ids[0] != u'':
            with get_session() as db_session:
                db_session.query(ImageSeriesRel).filter(
                    ImageSeriesRel.image_series_id == series_id,
                    ImageSeriesRel.image_id.in_(image_ids)
                ).delete(synchronize_session=False)
                db_session.commit()
        else:
            result.update({
                'response': 'fail',
                'info': u'请选择图片'
            })
        return jsonify(result)
    except Exception as e:
        print e
        abort(400)


# ———————————————————— 图片标签相关操作 ————————————————————
@manage.route('/image_tag_list', methods=['GET'])
def image_tag_list():
    result = {
        'response': 'ok',
        'image_tag_list': [],
        'info': '',
        'meta': {}
    }
    try:
        limit = 20
        page = request.args.get('page', 1)
        with get_session() as db_session:
            all_image_tag = db_session.query(ImageTags)
            paginator = SQLAlchemyPaginator(all_image_tag, limit)
            page = paginator.get_validate_page(page)

            _image_tag_list = list()
            for image_tag in paginator.page(page):
                image_tag_dict = image_tag.to_dict()
                all_association_tag = image_tag.all_association_tag
                all_association_tag_list = list()
                for association_tag in all_association_tag:
                    association_tag_dict = association_tag.to_dict()
                    all_association_tag_list.append(association_tag_dict)
                image_tag_dict['all_association_tag'] = all_association_tag_list

                _image_tag_list.append(image_tag_dict)
            result['image_tag_list'] = _image_tag_list

            result.update({
                'meta': {
                    'cur_page': page,
                    'all_page': paginator.max_page,
                    'count': paginator.count
                }
            })
        return jsonify(result)
    except Exception as e:
        print e
        abort(400)


# 标签详情
@manage.route('/image_tag_list/detail', methods=['GET'])
def get_image_tag_detail():
    result = {
        'response': 'ok',
        'info': '',
        'image_tag': ''
    }
    try:
        _id = request.args.get('id')
        with get_session() as db_session:
            image_tag = db_session.query(ImageTags).get(_id)
            if image_tag:
                image_tag_dict = image_tag.to_dict()
                result['image_tag'] = image_tag_dict
            else:
                result.update({
                    'response': 'fail',
                    'info': u'当前标签不存在'
                })
        return jsonify(result)
    except Exception as e:
        app.my_logger.error(traceback.format_exc(e))
        abort(400)


# 标签更新
@manage.route('/image_tag_list/update', methods=['POST'])
def update_image_tag_detail():
    result = {
        'response': 'ok',
        'info': ''
    }
    image_tag_id = request.form.get('id')
    image_tag_name = request.form.get('name')
    try:
        if None in [image_tag_name]:
            result.update({
                'response': 'fail',
                'info': u'请检查参数是否填写完整'
            })
        else:
            with get_session() as db_session:
                if not image_tag_id:
                    has_tag = db_session.query(ImageTags).filter(
                        ImageTags.name == image_tag_name
                    ).first()
                    if has_tag:
                        result['response'] = 'fail'
                        result['info'] = u'当前标签已存在'
                    else:
                        image_tag = ImageTags()
                        image_tag.name = image_tag_name
                        db_session.add(image_tag)
                else:
                    image_tag = db_session.query(ImageTags).get(image_tag_id)
                    if image_tag:
                        has_tag = db_session.query(ImageTags).filter(
                            ImageTags.name == image_tag_name
                        ).first()
                        if has_tag:
                            result['response'] = 'fail'
                            result['info'] = u'当前标签已存在'
                        else:
                            image_tag.name = image_tag_name
                    else:
                        result['response'] = 'fail'
                        result['info'] = u'当前对象不存在'
                db_session.commit()
        return jsonify(result)
    except Exception as e:
        app.my_logger.error(traceback.format_exc(e))
        abort(400)


# 删除标签
@manage.route('/image_tag_list/delete', methods=['POST'])
def delete_image_tag():
    result = {
        'response': 'ok',
        'info': ''
    }
    ids = request.form.get('ids').split(',')
    try:
        # 删除标签时，会将该标签中所有的标签与图片关系删除
        with get_session() as db_session:
            for _id in ids:
                image_tag = db_session.query(ImageTags).get(_id)
                if image_tag:
                    # 删除专题
                    db_session.delete(image_tag)

                    # 删除关系
                    db_session.query(ImageTagsRel).filter(
                        ImageTagsRel.image_tag_id == _id
                    ).delete(synchronize_session=False)
            db_session.commit()
        return jsonify(result)
    except Exception as e:
        print e
        abort(400)


# 标签图片
@manage.route('/image_tag_list/tag_image_list', methods=['GET'])
def tag_image_list():
    result = {
        'response': 'ok',
        'image_list': [],
        'meta': {}
    }
    limit = 40
    page = request.args.get('page', 1)
    tag_id = request.args.get('tag_id')
    try:
        with get_session() as db_session:
            query = db_session.query(Img).join(
                ImageTagsRel, Img.id == ImageTagsRel.image_id
            ).filter(
                ImageTagsRel.tag_id == tag_id
            )

            tag = db_session.query(ImageTags).get(tag_id)
            if tag:
                paginator = SQLAlchemyPaginator(query, limit)
                page = paginator.get_validate_page(page)

                _img_list = list()
                for img in paginator.page(page):
                    img_dict = img.to_dict()
                    img_series_obj = db_session.query(ImageSeriesRel).filter(
                        ImageSeriesRel.image_id == img.id
                    ).all()
                    img_series_name = [image_series.image_series_name for image_series in img_series_obj]
                    img_dict['image_series'] = img_series_name if img_series_name else [u'无']
                    img_dict['image_tag'] = [tag.name]
                    _img_list.append(img_dict)

                result.update({
                    'image_list': _img_list
                })

                result.update({
                    'meta': {
                        'cur_page': page,
                        'all_page': paginator.max_page,
                        'count': paginator.count
                    }
                })
            else:
                result['response'] = 'fail'
                result['info'] = u'当前标签不存在'

            return jsonify(result)
    except Exception as e:
        print e.message
        abort(400)


# 将图片移除标签
@manage.route('/image_tag_list/remove_image_from_tag', methods=['POST'])
def remove_image_from_tag():
    result = {
        'response': 'ok',
        'info': ''
    }
    try:
        image_ids = request.form.get('image_id', u'').split(',')
        tag_id = request.form.get('tag_id')
        if len(image_ids) > 0 and image_ids[0] != u'':
            with get_session() as db_session:
                db_session.query(ImageTagsRel).filter(
                    ImageTagsRel.tag_id == tag_id,
                    ImageTagsRel.image_id.in_(image_ids)
                ).delete(synchronize_session=False)
                db_session.commit()
        else:
            result.update({
                'response': 'fail',
                'info': u'请选择图片'
            })
        return jsonify(result)
    except Exception as e:
        print e
        abort(400)


@manage.route('/image_tag_list/image_association_tag', methods=['GET'])
def image_tag_association_list():
    result = {
        'response': 'ok',
        'association_tag_str': '',
        'tag_id': ''
    }
    try:
        tag_id = request.args.get('tag_id', None)
        result['tag_id'] = tag_id
        with get_session() as db_session:
            association_tag_query = db_session.query(ImageAssociationTag).filter(
                ImageAssociationTag.tag_id == tag_id
            ).all()
            if association_tag_query:
                association_tag_str = u'，'.join([association_tag.name for association_tag in association_tag_query])
                result['association_tag_str'] = association_tag_str
        return jsonify(result)
    except Exception as e:
        print e
        abort(400)


@manage.route('/image_tag_list/image_association_tag/update', methods=['POST'])
def image_tag_association_update():
    result = {
        'response': 'ok',
        'info': ''
    }
    try:
        tag_id = request.form.get('tag_id', None)
        association_tag_str = request.form.get('image_association_tag_str', '')
        if tag_id:
            with get_session() as db_session:
                db_session.query(ImageAssociationTag).filter(
                    ImageAssociationTag.tag_id == tag_id
                ).delete(synchronize_session=False)
                association_tag_list = association_tag_str.split(u'，')
                for association_tag in association_tag_list:
                    association_tag_obj = db_session.query(ImageAssociationTag).filter(
                        ImageAssociationTag.name == association_tag
                    ).first()
                    if not association_tag_obj:
                        association_tag_obj = ImageAssociationTag()
                        association_tag_obj.tag_id = tag_id
                        association_tag_obj.name = association_tag
                        db_session.add(association_tag_obj)
                db_session.commit()
        else:
            result.update({
                'response': 'fail',
                'info': u'未选择标签'
            })
        return jsonify(result)
    except Exception as e:
        print traceback.format_exc(e)
        abort(400)


# ———————————————————— 专题分类相关操作 ————————————————————
@manage.route('/image_series_category_list', methods=['GET'])
def image_series_category_list():
    result = {
        'response': 'ok',
        'image_series_category_list': [],
        'info': ''
    }
    try:
        with get_session() as db_session:
            all_image_series_category = db_session.query(ImageSeriesCategory).all()
            _image_series_category_list = list()
            for image_series_category in all_image_series_category:
                image_series_category_dict = image_series_category.to_dict()
                image_series = db_session.query(ImageSeriesCategoryRel).filter(
                    ImageSeriesCategoryRel.category_id == image_series_category.id
                ).all()
                count = len(image_series)
                image_series_category_dict['count'] = count
                _image_series_category_list.append(image_series_category_dict)
            result['image_series_category_list'] = _image_series_category_list
        return jsonify(result)
    except Exception as e:
        print e
        abort(400)


# 专题分类详情
@manage.route('/image_series_category_list/detail', methods=['GET'])
def get_image_series_category_detail():
    result = {
        'response': 'ok',
        'info': '',
        'image_series_category': ''
    }
    try:
        _id = request.args.get('id')
        with get_session() as db_session:
            data = db_session.query(ImageSeriesCategory).get(_id)
            if data:
                data_dict = data.to_dict()
                result['image_series_category'] = data_dict
            else:
                result.update({
                    'response': 'fail',
                    'info': u'当前标签不存在'
                })
        return jsonify(result)
    except Exception as e:
        app.my_logger.error(traceback.format_exc(e))
        abort(400)


# 专题分类更新
@manage.route('/image_series_category_list/update', methods=['POST'])
def update_image_series_category_detail():
    result = {
        'response': 'ok',
        'info': ''
    }
    image_series_category_id = request.form.get('id')
    image_series_category_name = request.form.get('name')
    image_series_category_desc = request.form.get('desc')
    now = datetime.datetime.now()
    try:
        if None in [image_series_category_name]:
            result.update({
                'response': 'fail',
                'info': u'请检查参数是否填写完整'
            })
        else:
            with get_session() as db_session:
                if not image_series_category_id:
                    image_series_category = ImageSeriesCategory()
                    image_series_category.name = image_series_category_name
                    image_series_category.desc = image_series_category_desc
                    db_session.add(image_series_category)
                else:
                    image_series_category = db_session.query(ImageSeriesCategory).get(image_series_category_id)
                    if image_series_category:
                        image_series_category.name = image_series_category_name
                        image_series_category.desc = image_series_category_desc
                        image_series_category.modified_date = now
                    else:
                        result['response'] = 'fail'
                        result['info'] = u'当前对象不存在'
                db_session.commit()
        return jsonify(result)
    except Exception as e:
        app.my_logger.error(traceback.format_exc(e))
        abort(400)


# 删除分类专题
@manage.route('/image_series_category_list/delete', methods=['POST'])
def delete_image_series_category():
    result = {
        'response': 'ok',
        'info': ''
    }
    ids = request.form.get('ids').split(',')
    try:
        # 删除分类专题时，会将该分类中的所有专题关系删除
        with get_session() as db_session:
            for _id in ids:
                image_series_category = db_session.query(ImageSeriesCategory).get(_id)
                if image_series_category:
                    # 删除专题分类
                    db_session.delete(image_series_category)

                    # 删除关系
                    db_session.query(ImageSeriesCategoryRel).filter(
                        ImageSeriesCategoryRel.category_id == _id
                    ).delete(synchronize_session=False)
            db_session.commit()
        return jsonify(result)
    except Exception as e:
        print e
        abort(400)


# 设置分类专题
@manage.route('/image_series_category_list/set', methods=['GET'])
def get_column_set():
    result = {
        'response': 'ok',
        'info': '',
        'image_series_category': '',
        'image_series_category_rel_list': []
    }
    _id = request.args.get('id')
    try:
        with get_session() as db_session:
            image_series_category = db_session.query(ImageSeriesCategory).get(_id)
            if image_series_category:
                image_series_category_dict = image_series_category.to_dict()
                result['image_series_category'] = image_series_category_dict
                all_category_series_rel_list = db_session.query(ImageSeriesCategoryRel, ImageSeries).join(
                    ImageSeries, ImageSeries.id == ImageSeriesCategoryRel.series_id
                ).filter(
                    ImageSeriesCategoryRel.category_id == image_series_category.id
                ).all()
                for category_series_rel, image_series in all_category_series_rel_list:
                    category_series_rel_dict = image_series.to_dict()
                    category_series_rel_dict['id'] = str(category_series_rel.id)
                    result['image_series_category_rel_list'].append(category_series_rel_dict)
            else:
                result.update({
                    'response': 'fail',
                    'info': u'当前分类不存在'
                })
        return jsonify(result)
    except Exception as e:
        print e


@manage.route('/image_series_category_list/set_update', methods=['POST'])
def set_update_column():
    result = {
        'response': 'ok',
        'info': ''
    }
    image_series_category_id = request.form.get('image_series_category_id')
    series_id_list = request.form.get('series_id_list')
    try:
        if None in [image_series_category_id, series_id_list]:
            result.update({
                'response': 'fail',
                'info': u'请检查参数是否填写完整'
            })
        else:
            ids = series_id_list.split(',')
            if ids[0]:
                with get_session() as db_session:
                    image_series_category = db_session.query(ImageSeriesCategory).get(image_series_category_id)
                    if image_series_category:
                        for series_id in ids:
                            image_series = db_session.query(ImageSeries).get(series_id)
                            image_series_category_rel = ImageSeriesCategoryRel()
                            image_series_category_rel.category_id = image_series_category_id
                            image_series_category_rel.series_id = series_id
                            image_series_category_rel.category_name = image_series_category.name
                            image_series_category_rel.series_name = image_series.name
                            db_session.add(image_series_category_rel)
                    db_session.commit()
        return jsonify(result)
    except Exception as e:
        print e


@manage.route('/image_series_category_list/set_delete', methods=['POST'])
def set_delete_column():
    result = {
        'response': 'ok',
        'info': ''
    }
    ids = request.form.get('ids').split(',')
    try:
        if ids[0]:
            with get_session() as db_session:
                db_session.query(ImageSeriesCategoryRel).filter(
                    ImageSeriesCategoryRel.id.in_(ids)
                ).delete(synchronize_session=False)
                db_session.commit()
        else:
            result.update({
                'response': 'fail',
                'info': u'当前未选择任何数据'
            })
        return jsonify(result)
    except Exception as e:
        print e


@manage.route('/image_recommend_tag_list', methods=['Get'])
def get_recommend_tag_list():
    result = {
        'response': 'ok',
        'image_recommend_tag_list': []
    }
    try:
        _image_recommend_tag_list = list()
        with get_session() as db_session:
            query = db_session.query(ImageRecommendTags).all()
            tags = db_session.query(ImageTags).join(
                ImageRecommendTagsRel, ImageRecommendTagsRel.tag_id == ImageTags.id
            )
            for image_recommend_tag in query:
                image_recommend_tag_id = image_recommend_tag.id
                _tags = tags.filter(
                    ImageRecommendTagsRel.recommend_tag_id == image_recommend_tag_id
                )
                tag_count = _tags.count()
                tag_member = ','.join([t.name for t in _tags])
                image_recommend_tag_dict = image_recommend_tag.to_dict()
                image_recommend_tag_dict['count'] = tag_count
                image_recommend_tag_dict['member'] = tag_member
                _image_recommend_tag_list.append(image_recommend_tag_dict)
            result['image_recommend_tag_list'] = _image_recommend_tag_list
        return jsonify(result)
    except Exception as e:
        print e


# 推荐标签组详情
@manage.route('/image_recommend_tag_list/detail', methods=['GET'])
def get_recommend_tag_detail():
    result = {
        'response': 'ok',
        'info': '',
        'image_recommend_tag': '',
        'tag_ids': [],
        'tag_names': []
    }
    try:
        _id = request.args.get('id')
        with get_session() as db_session:
            data = db_session.query(ImageRecommendTags).get(_id)
            if data:
                # 查找与之相关的标签
                tags = db_session.query(ImageTags).join(
                    ImageRecommendTagsRel, ImageRecommendTagsRel.tag_id == ImageTags.id
                ).filter(
                    ImageRecommendTagsRel.recommend_tag_id == _id
                ).all()
                tag_ids = [str(tag.id) for tag in tags]
                tag_names = [tag.name for tag in tags]
                data_dict = data.to_dict()
                result.update({
                   'image_recommend_tag': data_dict,
                    'tag_names': tag_names,
                    'tag_ids': tag_ids
                })
            else:
                result.update({
                    'response': 'fail',
                    'info': u'当前推荐标签组不存在'
                })
        return jsonify(result)
    except Exception as e:
        app.my_logger.error(traceback.format_exc(e))
        abort(400)


# 推荐标签组更新
@manage.route('/image_recommend_tag_list/update', methods=['POST'])
def update_image_recommend_tag_detail():
    result = {
        'response': 'ok',
        'info': ''
    }
    _id = request.form.get('id')
    name = request.form.get('name')
    tag_ids = request.form.get('tag_ids')
    tag_id_list = tag_ids.split(',')
    try:
        if None in [name] or not tag_id_list:
            result.update({
                'response': 'fail',
                'info': u'请检查参数是否填写完整'
            })
        else:
            with get_session() as db_session:
                if not _id:
                    _new_id = IdGenerator.gen()
                    recommend_tag = ImageRecommendTags()
                    recommend_tag.id = _new_id
                    recommend_tag.name = name
                    for tag_id in tag_id_list:
                        recommend_tag_rel = ImageRecommendTagsRel()
                        recommend_tag_rel.tag_id = tag_id
                        recommend_tag_rel.recommend_tag_id = _new_id
                        db_session.add(recommend_tag_rel)
                    db_session.add(recommend_tag)
                else:
                    recommend_tag = db_session.query(ImageRecommendTags).get(_id)
                    if recommend_tag:
                        recommend_tag.name = name
                        has_tags = db_session.query(ImageRecommendTagsRel).filter(
                            ImageRecommendTagsRel.recommend_tag_id == _id
                        ).all()
                        has_tag_id_list = set([str(tag.tag_id) for tag in has_tags])
                        # 删除的标签关系
                        del_tag_id_list = has_tag_id_list - set(tag_id_list)
                        db_session.query(ImageRecommendTagsRel).filter(
                            ImageRecommendTagsRel.tag_id.in_(del_tag_id_list)
                        ).delete(synchronize_session=False)
                        # 新增的标签关系
                        add_tag_id_list = set(tag_id_list) - has_tag_id_list
                        for add_tag_id in add_tag_id_list:
                            new_tags_rel = ImageRecommendTagsRel()
                            new_tags_rel.recommend_tag_id = _id
                            new_tags_rel.tag_id = add_tag_id
                            db_session.add(new_tags_rel)
                    else:
                        result['response'] = 'fail'
                        result['info'] = u'当前对象不存在'
                db_session.commit()
        return jsonify(result)
    except Exception as e:
        app.my_logger.error(traceback.format_exc(e))
        abort(400)


# 推荐标签组删除
@manage.route('/image_recommend_tag_list/delete', methods=['POST'])
def del_image_recommend_tag():
    result = {
        'response': 'ok'
    }
    ids = request.form.get('ids').split(',')
    try:
        if ids[0]:
            with get_session() as db_session:
                db_session.query(ImageRecommendTags).filter(
                    ImageRecommendTags.id.in_(ids)
                ).delete(synchronize_session=False)
                # 同时删除所有的关联关系
                for _id in ids:
                    db_session.query(ImageRecommendTagsRel).filter(
                        ImageRecommendTagsRel.recommend_tag_id == _id
                    ).delete(synchronize_session=False)
                db_session.commit()
        else:
            result.update({
                'response': 'fail',
                'info': u'当前未选择任何数据'
            })
        return jsonify(result)
    except Exception as e:
        print e

if __name__ == '__main__':
    pass
