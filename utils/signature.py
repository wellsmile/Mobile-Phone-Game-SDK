#coding=utf-8
'''
Created on Aug 27, 2016

@author: Felix
'''
import hmac

def get_signature(key, content):
    return hmac.new(key, content).hexdigest()