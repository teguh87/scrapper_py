import urlparse
import requests
import validators
import phonenumbers
import re
import os
import datetime
from bs4 import BeautifulSoup
import json

import logging
import logging.config

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s:%(levelname)s:%(message)s")

class scrapper(object):
	
	def __init__(self, url = None):
		if url is None:
			self.url = "http://stock.vietnammarkets.com/vietnam-stock-market.php"
		else:
			self.url = url 
		

	def __request(self, url):
		logging.debug('try to fetch content from: %s' %(url))
		req = requests.get(url)
		return BeautifulSoup(req.content, 'html.parser')

	def __query_table(self, className = None):
		soup = self.__request(self.url)
		if className is None:
			soup.find("table")
		else:
			soup.find("table", class_ = className)
		datas = soup.find("table")
		dicts = []
		for r in datas.findAll("tr"):
			cells = r.findAll("td")
			ticker_symbol = cells[0].findAll(text=True)
			company_name  = cells[1].findAll(text=True)
			url = [a['href'] for a in cells[0].find_all('a', href=True) if a.text]
			listing_borses = cells[2].findAll(text=True)
			dictr = {
					"ticker_symbol": ticker_symbol[0],
					"company_name": company_name[0],
					"url": ''.join(url),
					"listing_borses": listing_borses[0],
					"crawled_time": datetime.datetime.now().strftime("%m-%d-%Y")
				  }
			dicts.append(dictr)
		return dicts

	def __query_table_detail(self, url):

		soup = self.__request(url)
		tabel = soup.find("table")	
		tabel_raw = tabel.findAll(text=True)
		tabel_cleaned = map(lambda s: s.strip(), tabel_raw)
		very_cleaned = [x for x in tabel_cleaned if x != '']

		dic = {}
		dic['financial_summary'] = {}
		dic['auditing_company'] = {}
		dic['business_registration'] = {}
		idx = 0
		for line in very_cleaned:
			if re.search(r'Company Profile', line) : 
				dic['company_name'] = very_cleaned[idx + 1]
				dic['company_url']  = url
				dic['ticker_symbol'] = urlparse.urlparse(url).path.split('/')[2]
				dic['company_address'] = {
					'street1' : very_cleaned[idx + 2].split(',')[0] if len(very_cleaned[idx + 2].split(',')) >= 1 else '',
					'street2': very_cleaned[idx + 2].split(',')[1] if len(very_cleaned[idx + 2].split(',')) >= 2 else '',
					'city': very_cleaned[idx + 2].split(',')[2] if len(very_cleaned[idx + 2].split(',')) >= 3 else '',
					'province': very_cleaned[idx + 2].split(',')[3] if len(very_cleaned[idx + 2].split(',')) >= 4 else ''
				}
				dic['company_phone_number'] = very_cleaned[3] + '/' + very_cleaned[4]
				try:
					dic['company_phone_number'] = self.__phone_formating(very_cleaned[idx + 3]) + '/' + self.__phone_formating(very_cleaned[idx + 4])
				except :
					pass
			
			email_patt = re.compile(r"\"?([-a-zA-Z0-9.`?{}]+@\w+\.\w+)\"?")
			if email_patt.match(line) :
				dic['company_email'] = line

			web_patt =  re.compile(
				r'^(?:http|ftp)s?://' # http:// or https://
				r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
				r'localhost|' #localhost...
				r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
				r'(?::\d+)?' # optional port
				r'(?:/?|[/?]\S+)$', re.IGNORECASE)


			if re.search(r'^(?:http|ftp)s?://', line):
				if web_patt.match(line):
					dic['company_website'] = line					
			else:
				if web_patt.match('http://'+ line):
					dic['company_website'] = line
			
			if re.search(r'Capital Currency', line):
				capital_currency = very_cleaned[idx + 1] 
				dic['financial_summary'].update({
					'capital_currency' : capital_currency
				})
			
			if re.search(r'Market Cap', line):
				market_capital = very_cleaned[idx + 1] 
				dic['revenue'] = market_capital
				dic['financial_summary'].update({
					'market_capital' : market_capital
				})
			
			if re.search(r'Par Value', line):
				par_value = very_cleaned[idx + 1] 
				dic['financial_summary'].update({
					'par_value' : par_value
				})

			if re.search(r'Equity', line):
				equity = very_cleaned[idx + 1] 
				dic['financial_summary'].update({
					'equity' : equity
				})
				 
			if re.search(r'Listing Volume', line):
				listed_volume = very_cleaned[idx + 1] 
				dic['financial_summary'].update({
					'listing_volume' : listed_volume
				})

			if re.search(r'Initial Listed Price', line):
				initial_listed_price = very_cleaned[idx + 1] 
				dic['financial_summary'].update({
					'initial_list_price' : initial_listed_price
				})
			
			if re.search(r'Business Summary', line) :
				desc = very_cleaned[idx + 1] 
				dic['company_description'] = desc

			if re.search(r'Auditing Company', line) :
				auditing_company_name = very_cleaned[idx + 1]
				company_address = very_cleaned[idx + 2]
				tmp_audit_company_contact = very_cleaned[idx + 3]
				split_audit_compnay_phone = tmp_audit_company_contact[0].split(' ')
				audit_company_contact = tmp_audit_company_contact
				try:
					audit_company_contact = self.__phone_formating(''.join(split_audit_compnay_phone[1:4])) + ' line. ' + 			''.join(re.findall(r'\d+', split_audit_compnay_phone[5]))
				except :
					pass

				
				split_audit_compnay_website = ''
				split_audit_compnay_email = ''
				try:
					tmp_audit_company_electronic = very_cleaned[idx + 4].split('-')
					split_audit_compnay_website =tmp_audit_company_electronic[0].split(':')[2]
					split_audit_compnay_email = tmp_audit_company_electronic[1].split(':')[1]
				except:
					pass

				dic['auditing_company'].update({
					'company_name' : auditing_company_name,
					'company_address': company_address,
					'company_contact': audit_company_contact,
					'company_website': 'http:'+ split_audit_compnay_website,
					'company_email': split_audit_compnay_email 
				})
			
			if re.search(r'Business Registration', line):
				established_licence = very_cleaned[idx + 1]
				business_licence = very_cleaned[idx + 2]
				dic['business_registration'].update({
					'established_licence': established_licence,
					'business_licance': business_licence
				})

			idx += 1
		
		return dic
		
	def __phone_formating(self, number):
		number = ''.join(re.findall(r'\d+', number))
		format_phone = phonenumbers.format_number(phonenumbers.parse(number, 'VN'), 
					phonenumbers.PhoneNumberFormat.INTERNATIONAL)
		return format_phone
		
	def print_toJson(self, type = 'index'):
		tables = self.__query_table()
		filename = 'company_%s.json'%(type)
		lists = []
		try:
			if tables is not None:
				if not (type == 'index'):
					for tab in tables:
						if(tab['url']):
							url = tab['url']
							q = self.__query_table_detail(url)
							lists.append(q)
				else:
					lists = tables
			
		except Exception as e:
			print(e)

		try:
			os.remove(filename)
			logging.debug("Remove file %s"%(filename))
		except OSError as e:
			logging.error("error has been aquire message %s"%(str(e)))

		with open(filename, 'w') as outfile:
			logging.debug("Save file %s"%(filename))
			json.dump(lists, outfile)

if __name__ == '__main__':
	scr = scrapper()
	scr.print_toJson(type = 'profiles')

	
