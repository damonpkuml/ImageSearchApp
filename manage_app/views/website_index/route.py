# coding:utf-8

from flask import Blueprint

website = Blueprint('website', __name__, static_folder='templates')
