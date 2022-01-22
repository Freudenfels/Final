# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016-TODAY Steigend IT Solutions
#    For more details, check COPYRIGHT and LICENSE files
#
##############################################################################

import binascii
import time
from urllib import request #, urlopen, URLError
from urllib.request import urlopen
from urllib.error import URLError
import xml.etree.ElementTree as etree
import unicodedata

from suds import WebFault
from suds.client import Client
from suds.sax.attribute import Attribute
from suds.plugin import MessagePlugin
from suds.sax.element import Element
from suds.transport.http import HttpAuthenticated

from odoo import fields, _
from odoo.exceptions import Warning,ValidationError
import re
import logging
_logger= logging.getLogger(__name__)


class NamespaceModificationPlugin(MessagePlugin):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
 
    def marshalled(self, context):
        for paths, ns in self.kwargs.get('services', []):
            node = None
            for path in paths:
                if node == None:
                    node = context.envelope
                node = node.getChild(path)
            if not node is None:
                node.setPrefix(ns)
                node.attributes.append(Attribute('xmlns:%s'%ns, context.envelope.nsprefixes[ns]))


class LogPlugin(MessagePlugin):

    def sending(self, context):
        _logger.info(str(context.envelope)) 

class DHLPaketProvider():

    def __init__(self, username, password, user, signature, test_mode=True):
        location = False
        if test_mode:
            location = 'https://cig.dhl.de/services/sandbox/soap'
        else:
            location = 'https://cig.dhl.de/services/production/soap'
        url = 'https://cig.dhl.de/cig-wsdls/com/dpdhl/wsdl/geschaeftskundenversand-api/2.2/geschaeftskundenversand-api-2.2.wsdl'

        t = HttpAuthenticated(username=username, password=password)
        
#         versionDD = (['Body', 'CreateShipmentDDRequest', 'Version'], 'ns0')
#         versionDeleteDD = (['Body', 'DeleteShipmentDDRequest', 'Version'], 'ns0')
#         versionTD = (['Body', 'CreateShipmentTDRequest', 'Version'], 'ns0')
        
        VEKP = (['Body', 'ValidateShipmentOrderRequest', 'ShipmentOrder', 'Shipment', 'ShipmentDetails', 'accountNumber'], 'ns0')
        VNAME = (['Body', 'ValidateShipmentOrderRequest', 'ShipmentOrder', 'Shipment', 'Receiver', 'name1'], 'ns0')
        REKP = (['Body', 'CreateShipmentOrderRequest', 'ShipmentOrder', 'Shipment', 'ShipmentDetails', 'accountNumber'], 'ns0')
        RNAME = (['Body', 'CreateShipmentOrderRequest', 'ShipmentOrder', 'Shipment', 'Receiver', 'name1'], 'ns0')
        RDelete = (['Body', 'DeleteShipmentOrderRequest', 'shipmentNumber'], 'ns0')
#         partnerIDDD = (['Body', 'CreateShipmentDDRequest', 'ShipmentOrder', 'Shipment', 'ShipmentDetails', 'Attendance', 'partnerID'], 'ns0')
        
        self.client = Client(
            url, transport=t, location=location, cache=None, 
            plugins=[
#                 LogPlugin(),
                NamespaceModificationPlugin(services=[
#                     versionDD, 
#                     versionTD, 
                    VEKP, 
                    VNAME,
                    REKP,
                    RNAME,
                    RDelete,
#                     partnerIDDD, 
#                     versionDeleteDD
                    ])
                ])
        self.client.options.prettyxml = True
        ns0 = ('ns0', 'http://dhl.de/webservice/cisbase')
        authentification = Element('Authentification', ns=ns0)
        user = Element('user', ns=ns0).setText(user)
        signature = Element('signature', ns=ns0).setText(signature)
#         ttype = Element('type', ns=ns0).setText('0')
         
#         authentification.insert(ttype)        
        authentification.insert(signature)
        authentification.insert(user)
         
        self.client.set_options(soapheaders=[authentification])


#     def _convert_weight(self, weight, weight_unit):
#         if weight_unit == "LB":
#             return round(weight * 2.20462, 3)
#         else:
#             return round(weight, 3)

    def rate_request(self, order, carrier):
        # DHL DE does not provide rate request api, so returning price as zero
        dict_response = {'price': 0.0,
                         'currency': order.currency_id.name,
                         'error_found': False}
        return dict_response
    

        
    def _get_version(self):
        version = self.client.service.getVersion()
#         version.majorRelease = 2
#         version.minorRelease = 2
        return version

    def _get_acc_no(self, carrier):
        product_procedure_dict = {
            'V01PAK': '01', # Paket National
            'V01PRIO': '01',
            'V53WPAK': '53', # Weltpaket
            'V54EPAK': '54', # Europaket
            'V55PAK': '55', # DHL Paket connect
            'V06PAK': '06', # DHL PAKET Taggleich
            'V06TG': '01', # Kurier Taggleich
            'V06WZ': '01', # Kurier Wunschzeit
            'V86PARCEL': '86', # DHL Paket Austria
            'V87PARCEL': '87', # DHL PAKET Connect
            'V82PARCEL': '82' # DHL PAKET International
        }
        procedure_no = product_procedure_dict[carrier.dhl_de_paket_product_code]
        account_number = "%s%s%s"%(carrier.dhl_de_paket_account_number,procedure_no,carrier.dhl_de_paket_partner_no)
        return account_number

    def _get_shipment_items(self, picking, carrier):
        result = []
        if getattr(picking,'package_ids',False):
            for package in picking.package_ids:
                shipmentItem = self.client.factory.create('ShipmentItemType')
                shipmentItem.weightInKG = package.weight
                shipmentItem.lengthInCM = carrier.dhl_de_paket_package_length
                shipmentItem.widthInCM = carrier.dhl_de_paket_package_width
                shipmentItem.heightInCM = carrier.dhl_de_paket_package_height
#                 shipmentItem.PackageType = carrier.dhl_de_paket_package_type
                result.append(shipmentItem)
        else:
            shipmentItem = self.client.factory.create('ShipmentItemType')
            shipmentItem.weightInKG = picking.weight
            shipmentItem.lengthInCM = carrier.dhl_de_paket_package_length
            shipmentItem.widthInCM = carrier.dhl_de_paket_package_width
            shipmentItem.heightInCM = carrier.dhl_de_paket_package_height
#             shipmentItem.PackageType = carrier.dhl_de_paket_package_type
            result.append(shipmentItem)
        return result
    
    def _get_services(self, picking, carrier):
        # Limited or no documentation
#         <Service>
#                      <!--You may enter the following 16 items in any order-->
#                      <!--Optional:-->
#                      <VisualCheckOfAge active="1" type="A16"/>
#                      <!--Optional:-->
#                      <PreferredLocation active="0" details="?"/>
#                      <!--Optional:-->
#                      <PreferredNeighbour active="0" details="?"/>
#                      <!--Optional:-->
#                      <GoGreen active="1"/>
#                      <!--Optional:-->
#                      <Personally active="0"/>
#                      <CashOnDelivery active="1" codAmount="23.25"/>
#                      <!--Optional:-->
#                      <AdditionalInsurance active="1" insuranceAmount="2500"/>
#                      <!--Optional:-->
#                      <BulkyGoods active="1"/>
        return None

    def _get_notifications(self, picking):
        notification = self.client.factory.create('ShipmentNotificationType')
        notification.recipientEmailAddress = picking.partner_id.email or None
        return notification
    
    def _get_bank_data(self, picking, carrier):
        # Needed only in case of COD
        bankData = self.client.factory.create('ns0:BankType')
        # bankData.accountOwner = None
        # bankData.accountreference = None
        # bankData.bankCode = None
        # bankData.bankName = None
        # bankData.iban = None
        # bankData.note1 = None
        # bankData.bic = None
        return bankData

    def _get_shipment_details(self, picking, carrier):
        shipmentDetails = self.client.factory.create('ShipmentDetailsTypeType')
        shipmentDetails.product = carrier.dhl_de_paket_product_code
        shipmentDetails.shipmentDate = picking.date_done and picking.date_done > fields.Datetime.now() and picking.date_done.split(' ')[0] or fields.Date.today()
        shipmentDetails.accountNumber = self._get_acc_no( carrier)
        shipmentDetails.customerReference = picking.origin and picking.origin[:35] or picking.name[:35]
#         shipmentDetails.returnShipmentAccountNumber = None
#         shipmentDetails.returnShipmentReference = None#35size
        
        shipmentDetails.ShipmentItem = self._get_shipment_items(picking, carrier)
        shipmentDetails.Service = self._get_services(picking, carrier)
        shipmentDetails.Notification = self._get_notifications(picking)
        # shipmentDetails.NotificationEmailText = None
        shipmentDetails.BankData = self._get_bank_data(picking, carrier)
        return shipmentDetails
    
    def _getNameobj(self,partner):
        Name = self.client.factory.create('ns0:NameType')
        Name.name1 = partner.name[:50]
        if partner.parent_id:
            Name.name2 = partner.parent_id.name[:50]
        # company.name2 = None
#         company.Company = Company
        return Name
    
    def _split_address(self, address,street_name=False):
        street_number = False
        address = address.strip()
        if address.isdigit():
            street_number = address
            return street_name, street_number
        street_split = address.split()
        if len(street_split) > 1:
            if street_split[-1].isdigit():
                street_number = street_split.pop()
                street_name = ' '.join(street_split)
            elif street_split[0].isdigit():
                street_number = street_split.pop(0)
                street_name = ' '.join(street_split)
            else:
                street_name = ' '.join(street_split)
#         else:
#             street_name = address
        #need to remove the top part in the future
        if not street_number: 
            street_split = address.split('.')
            if len(street_split) > 1:
                if street_split[-1].isdigit():
                    street_number = street_split.pop()
                    street_name = '.'.join(street_split)
                elif street_split[0].isdigit():
                    street_number = street_split.pop(0)
                    street_name = '.'.join(street_split)
                else:
                    street_name = ' '.join(street_split)
        if not street_number:
            nstreet_split = re.findall(r'^(\D+)[\s\.]([\d\-\s]+(\s*[^\d\s]+)*)$', address)
            if nstreet_split:
                street_split = list(nstreet_split[0])
                street_split.pop()
                street_number = street_split.pop()
                street_name = ' '.join(street_split)
        if not street_number:
            nstreet_split = re.findall(r'^([\d\-\s]+)\s(\D+(\s*[^\d\s]+)*)$', address)
            if nstreet_split:
                street_split = list(nstreet_split[0])
                street_split.pop()#3items,last one is the street abrivations
                street_number = street_split.pop(0)
                street_name = ' '.join(street_split)
                #street_number = street_split[1]
                #street_name = street_name and street_name + ' '+ street_split[0] or street_split[0]
        if not street_number and not street_name:
            street_name = address
        return street_name, street_number
    
    def _get_origin_from_partner(self, partner):
        origin = self.client.factory.create('ns0:CountryType')
#         origin.country = partner.country_id.name
        origin.countryISOCode = partner.country_id and partner.country_id.code
        # origin.state = None
        return origin
    
    def _get_address_from_partner(self, partner):
        address_dict = {}
#         address = self.client.factory.create('ns0:NativeAddressType')
        
        street_name = False
        street_number = False
        careof = False
        if partner.street:
            street_name, street_number = self._split_address(partner.street.strip(),street_name)
        if street_number and street_name:
            if partner.street2:
                careof = partner.street2.strip()
        elif not street_number:
            if partner.street2:
                street_name2, street_number2 = self._split_address(partner.street2.strip(),False)
                if street_name2:
                    careof = street_name
                    street_name = street_name2
                if street_number2:
                    street_number = street_number2
        elif not street_name:
            if partner.street2:
                street_name2, street_number2 = self._split_address(partner.street2.strip(),street_name)
                if street_number2:
                    careof = street_number
                    street_number = street_number2
                if street_name2:
                    street_name = street_name2
        if not street_name:
            raise Warning(_("No Street Name\nPlease specify street name and street number for partner: %s"%partner.name))
        address_dict.update(streetName = street_name[:35],careof=None)
        if not street_number:
            raise Warning(_("No Street Number\nPlease add street number  for partner: %s"%partner.name))
        
        #if not partner.street.isdigit():
        #    raise Warning(_("Street Number must be digit\nPlease enter street number as digit for partner: %s (id: %s)"%(partner.name, partner.id)))
        
        if len(street_number) > 5:
            raise Warning(_("Invalid Street Number\nStreet Number cannot be more than 5 digits for partner: %s"%partner.name))
        address_dict.update(streetNumber = street_number)
        if not careof:
            careof = partner.parent_id and partner.parent_id.name or False
        if careof:
            address_dict.update(careof = careof[:35] or None)
        if not partner.zip:
            raise Warning(_("No Zip\nPlease add zip for partner: %s "%(partner.name)))
        if not partner.country_id:
            raise Warning(_("No Country\nPlease add country for partner: %s "%(partner.name)))
#         address.Zip = self.client.factory.create('ns1:Zip')
#         address.dispatchingInformation = None
        address_dict.update(zip = partner.zip.strip()[:10])
        
            
        if not partner.city:
            raise Warning(_("No City\nPlease add city for partner: %s"%(partner.name)))
        address_dict.update(city = partner.city.strip()[:35])
#         if partner.country_id.code == 'DE':
#             address.Zip.germany = partner.zip
#         elif partner.country_id.code == 'GB':
#             address.Zip.england = partner.zip
#         else:
#             address.Zip.other = partner.zip
        address_dict.update(countryISOCode = partner.country_id.code)
        # address.district = None
#         address.Origin = self._get_origin_from_partner(partner)
        # address.floorNumber = None
        # address.roomNumber = None
        # address.languageCodeISO = None
        # address.note = None
        return address_dict
    
    def _get_communication(self, partner):
        communication = self.client.factory.create('ns0:CommunicationType')
        if partner.phone:   
            communication.phone = partner.phone[:20] 
        elif partner.mobile:
            communication.phone = partner.mobile[:20] or None
        if partner.email:
            communication.email = partner.email[:70] or None
#         communication.contactPerson =  None
        
        contact = partner
        if partner.child_ids:
            contact = partner.child_ids[0] # Can be changed to configuration
            
        communication.contactPerson = contact.name.strip()[:50] or None
         
        return communication
    
    def _get_address(self, partner):
        address_dict = self._get_address_from_partner(partner)
        address = self.client.factory.create('ns0:NativeAddressType')
        address.streetName = address_dict['streetName']
        address.streetNumber = address_dict['streetNumber']
        address.zip = address_dict['zip']
        address.city = address_dict['city']
        address.addressAddition = address_dict['careof']
#         address.countryISOCode = address_dict['countryISOCode']
        address.Origin = self._get_origin_from_partner(partner)
        return address
    
    def _get_shipper(self, picking, carrier):
        shipper = self.client.factory.create('ShipperType')
        shipper_partner = picking.picking_type_id and picking.picking_type_id.warehouse_id.partner_id 
        shipper.Name = self._getNameobj(shipper_partner)
        shipper.Address = self._get_address(shipper_partner)
        shipper.Communication = self._get_communication(shipper_partner)
        # shipper.VAT = None
        # shipper.Remark = None
        return shipper
    
    def _get_receiver_packstation(self, partner):
        packstation = self.client.factory.create('ns0:PackStationType')
        postnumber = [num for num in partner.street.split() if num.isdigit()][-1]
        packstationnumber = partner.street2.split()[-1]
        packstation.postNumber = postnumber
        packstation.packstationNumber = packstationnumber
        packstation.zip = partner.zip.strip()
        packstation.city = partner.city.strip()
#         packstation = self.client.factory.create('ns1:PackStationType')
#         packstation.number = '25536775'
#         packstation.stationID = '101'
#         packstation.city = 'Koblenz'
#         packstation.Zip = '56076'
        packstation.Origin = self._get_origin_from_partner(partner)
        return packstation
    
    
    def update_receiver_address_packstation(self, receiver, partner):
        if (partner.street and 'packstation' in partner.street.lower()) or \
                        (partner.street2 and 'packstation' in partner.street2.lower()):
            receiver.Packstation = self._get_receiver_packstation(partner)
        else:
            receiver.Address = self._get_address(partner)
        return receiver
    
    def _get_receiver(self, picking, carrier):
        receiver = self.client.factory.create('ReceiverType')
        partner = picking.partner_id
        receiver.name1 = partner.name[:50]
        receiver.Communication = self._get_communication(partner)
        
#         receiver.Company.Person = self._get_receiver_person(partner)
        receiver = self.update_receiver_address_packstation(receiver, partner)
#         receiver.Address = self._get_receiver_address(partner)
#         receiver.Communication = self._get_receiver_communication(partner)
        #receiver.VAT = None
        #receiver.CompanyName3 = None
        return receiver
    
    
    def _get_export_document(self, picking, carrier):
        exportDocument = self.client.factory.create('ExportDocumentType')
        
        # exportDocument.invoiceNumber = None
        # exportDocument.exportType = None
        # exportDocument.exportTypeDescription = None
        # exportDocument.ExportType = None
        # exportDocument.termsOfTrade = None
        # exportDocument.placeOfCommital = None
        # exportDocument.additionalFee = None
        # exportDocument.permitNumber = None
        # exportDocument.attestationNumber = None
        # exportDocument.CountryCodeOrigin = None
        # exportDocument.WithElectronicExportNtfctn = = 
#             (Serviceconfiguration){
#                _active = ""
#             }
        # exportDocument.ExportDocPosition = None
        return exportDocument

    def _get_shipment(self, picking, carrier):
        shipment = self.client.factory.create('Shipment')
        shipment.ShipmentDetails = self._get_shipment_details(picking, carrier)
        shipment.Shipper = self._get_shipper(picking, carrier)
        shipment.Receiver = self._get_receiver(picking, carrier)
        shipment.ReturnReceiver = self._get_shipper(picking, carrier)
        shipment.ExportDocument = self._get_export_document(picking, carrier)
#         shipment.Identity = self._get_identity(picking, carrier)
#         shipment.FurtherAddresses = self._get_further_addresses(picking, carrier)
        return shipment
    
    def _get_shipment_order(self, picking, carrier):
        shipmentOrder = self.client.factory.create('ShipmentOrderType')
        shipmentOrder.sequenceNumber = 1
        shipmentOrder.Shipment = self._get_shipment(picking, carrier)
#         shipmentOrder.Pickup = self._getPickup()
        
        shipmentOrder.labelResponseType = 'URL'
        shipmentOrder.PrintOnlyIfCodeable = None
        return shipmentOrder
    
    def _get_shipment_orders(self, picking, carrier):
        shipmentOrder = self._get_shipment_order(picking, carrier)
        return [shipmentOrder]
    
    def validate_shipping(self, picking, carrier):
        version = self._get_version()
        shipmentOrders = self._get_shipment_orders(picking, carrier)
        response = self.client.service.validateShipment(version, shipmentOrders)
        return response
    
    def create_shipment(self, picking, carrier):
        version = self._get_version()
        shipmentOrders = self._get_shipment_orders(picking, carrier)
        response = self.client.service.createShipmentOrder(version, shipmentOrders)
        return response
    
    def send_shipping(self, picking, carrier):
        return self.create_shipment(picking, carrier)
    

    def delete_shipment(self, picking, carrier):
        version = self._get_version()
        shipmentNumber = picking.carrier_tracking_ref
        response = self.client.service.deleteShipmentOrder(version, shipmentNumber)
        return response



    def send_cancelling(self, picking, carrier):
        dict_response = {'carrier_tracking_ref': 0.0, 'price': 0.0, 'currency': False}
        return dict_response

    def _remove_accents(self, input_str):
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        only_ascii = nfkd_form.encode('ASCII', 'ignore')
        return only_ascii
