#coding=utf-8

import geoip2.database

class MatrixIP(object):
    def __init__(self, dbfile='GeoLite2-City.mmdb'):
        self.reader = geoip2.database.Reader(dbfile)
    
    def parse(self, ip):
        response = self.reader.city(ip)
        print(dir(response))
        return response.country.name, response.city.name, response.location.time_zone
    
if __name__ == '__main__':
    matrixIP = MatrixIP('/Users/Felix/Downloads/GeoLite2-City.mmdb')
    print(matrixIP.parse('116.213.171.173'))