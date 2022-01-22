# -*- coding: utf-8 -*-
##############################################################################
#
#    ODOO, Open Source Management Solution
#    Copyright (C) 2016 - 2020 Steigend IT Solutions (Omal Bastin)
#    Copyright (C) 2020 - Today O4ODOO (Omal Bastin)
#    For more details, check COPYRIGHT and LICENSE files
#
##############################################################################

# Updated to business customer shipping api 3.1

from urllib.error import URLError
import unicodedata

from suds.client import Client
from suds.sax.attribute import Attribute
from suds.plugin import MessagePlugin
from suds.sax.element import Element
from suds.transport.http import HttpAuthenticated

from odoo import fields, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, AccessError
import re
import os
import logging

_logger = logging.getLogger(__name__)


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
                node.attributes.append(Attribute('xmlns:%s' % ns, context.envelope.nsprefixes[ns]))


class LogPlugin(MessagePlugin):
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger

    def sending(self, context):
        self.debug_logger(context.envelope, 'dhl_paket_request')

    def received(self, context):
        self.debug_logger(context.reply, 'dhl_paket_response')


class DHLPaketProvider():

    def __init__(self, username, password, user, signature, test_mode, debug_logger):
        self.debug_logger = debug_logger
        self.username, self.password = username, password
        self.user, self.signature = user, signature
        if test_mode:
            self.location = 'https://cig.dhl.de/services/sandbox/soap'
        else:
            self.location = 'https://cig.dhl.de/services/production/soap'
        # self.url = 'https://cig.dhl.de/cig-wsdls/com/dpdhl/wsdl/geschaeftskundenversand-api/3.1"
        # "/geschaeftskundenversand-api-3.1.wsdl'

        self.wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                      '../api/geschaeftskundenversand-api-3.1.6.wsdl')
        self.client = False

    def login(self, limit=5):
        """while loop to get the connection successfully"""
        while True:
            try:
                self.intraship_login()
                break
            except URLError as err:
                if limit > 0:
                    limit -= 1
                    continue
                else:
                    raise AccessError(_(u'Network Error:\n\n{}').format(err))

    def intraship_login(self):
        t = HttpAuthenticated(username=self.username, password=self.password)

        #         versionDD = (['Body', 'CreateShipmentDDRequest', 'Version'], 'ns0')
        #         versionDeleteDD = (['Body', 'DeleteShipmentDDRequest', 'Version'], 'ns0')
        #         versionTD = (['Body', 'CreateShipmentTDRequest', 'Version'], 'ns0')

        VEKP = (['Body', 'ValidateShipmentOrderRequest', 'ShipmentOrder', 'Shipment',
                 'ShipmentDetails', 'accountNumber'],'ns0')
        VNAME = (['Body', 'ValidateShipmentOrderRequest', 'ShipmentOrder',
                  'Shipment', 'Receiver', 'name1'], 'ns0')
        REKP = (['Body', 'CreateShipmentOrderRequest', 'ShipmentOrder', 'Shipment',
            'ShipmentDetails', 'accountNumber'], 'ns0')
        RNAME = (['Body', 'CreateShipmentOrderRequest', 'ShipmentOrder',
                  'Shipment', 'Receiver', 'name1'], 'ns0')
        RDelete = (['Body', 'DeleteShipmentOrderRequest', 'shipmentNumber'], 'ns0')
        #         partnerIDDD = (['Body', 'CreateShipmentDDRequest', 'ShipmentOrder', 'Shipment', 'ShipmentDetails', 'Attendance', 'partnerID'], 'ns0')

        self.client = Client('file:///%s' % self.wsdl_path.lstrip('/'), transport=t, location=self.location, cache=None,
                             plugins=[
                                 LogPlugin(self.debug_logger),
                                 NamespaceModificationPlugin(services=[
                                     VEKP,
                                     VNAME,
                                     REKP,
                                     RNAME,
                                     RDelete,
                                 ])
                             ])

        self.client.options.prettyxml = True
        ns0 = ('ns0', 'http://dhl.de/webservice/cisbase')
        authentification = Element('Authentification', ns=ns0)
        user = Element('user', ns=ns0).setText(self.user)
        signature = Element('signature', ns=ns0).setText(self.signature)

        authentification.insert(signature)
        authentification.insert(user)

        self.client.set_options(soapheaders=[authentification])

    def rate_request(self, order, carrier):
        # DHL DE does not provide rate request api, so returning price as zero
        dict_response = {'price': 0.0,
                         'currency': order.currency_id.name,
                         'error_found': False}
        return dict_response

    def _get_version(self):
        version = self.client.service.getVersion()
        return version

    def _get_acc_no(self, carrier):
        product_procedure_dict = {
            'V01PAK': '01',  # Paket National
            'V01PRIO': '01',
            'V53WPAK': '53',  # Weltpaket
            'V54EPAK': '54',  # Europaket
            'V55PAK': '55',  # DHL Paket connect
            'V06PAK': '06',  # DHL PAKET Taggleich
            'V06TG': '06',  # Kurier Taggleich
            'V06WZ': '06',  # Kurier Wunschzeit
            'V86PARCEL': '86',  # DHL Paket Austria
            'V87PARCEL': '87',  # DHL PAKET Connect
            'V82PARCEL': '82',  # DHL PAKET International
            'V62WP': '62'  # DHL Warenpost
        }
        procedure_no = product_procedure_dict[carrier.dhl_de_paket_product_code]
        account_number = "%s%s%s" % (carrier.dhl_de_paket_account_number, procedure_no,
                                     carrier.dhl_de_paket_partner_no)
        return account_number

    def get_shipment_item(self, shipment_item):
        shipmentItem = self.client.factory.create('ShipmentItemType')
        shipmentItem.weightInKG = shipment_item['weightInKG']
        shipmentItem.lengthInCM = shipment_item['lengthInCM']
        shipmentItem.widthInCM = shipment_item['widthInCM']
        shipmentItem.heightInCM = shipment_item['heightInCM']
        return shipmentItem

    def _get_shipment_items(self, picking, carrier):
        result = []
        # package_details = []
        # pieceNumber = 1
        move_lines_with_package = picking.move_line_ids.filtered(lambda ml: ml.result_package_id)
        move_lines_without_package = picking.move_line_ids - move_lines_with_package
        if move_lines_without_package:
            packaging = carrier.dhl_de_paket_default_packaging_id
            weight = picking.weight_bulk
            weight = carrier._dhl_de_paket_convert_weight(weight, carrier.dhl_de_paket_package_weight_unit)
            result.append(dict(weightInKG = weight,
                               lengthInCM = packaging.packaging_length or carrier.dhl_de_paket_package_length,
                               widthInCM=packaging.width or carrier.dhl_de_paket_package_width,
                               heightInCM=packaging.height or carrier.dhl_de_paket_package_height,
                               name= picking.name,
                               move_lines_without_package=True,
                               package=packaging
                               ))
            # result.append(shipmentItem)
        if move_lines_with_package:
            # Generate shipment for each package in picking.
            for package in picking.package_ids:
                packaging = package.packaging_id or carrier.dhl_de_paket_default_packaging_id
                # compute move line weight in package
                move_lines = picking.move_line_ids.filtered(lambda ml: ml.result_package_id == package)
                weight = package.shipping_weight or package.weight
                weight = carrier._dhl_de_paket_convert_weight(weight, carrier.dhl_de_paket_package_weight_unit)
                result.append(dict(weightInKG=weight,
                                   lengthInCM=packaging.packaging_length or carrier.dhl_de_paket_package_length,
                                   widthInCM=packaging.width or carrier.dhl_de_paket_package_width,
                                   heightInCM=packaging.height or carrier.dhl_de_paket_package_height,
                                   name="%s" % package.name,
                                   move_lines_without_package=False,
                                   package=packaging
                                   ))

        return result

    def _get_services(self, picking, carrier, package_details):
        # Service elements available are IndividualSenderRequirement: This service is used exclusively for
        # shipments with special delivery requirements. It is not available for our regular business customers.,
        # PackagingReturn: Service for package return. For packagingReturn you also have to book a return label.,
        # Endorsement: Service "Endorsement". Mandatory for shipments with product DHL Paket International: V53WPAK.,
        # VisualCheckOfAge: Service visual age check.,
        # PreferredLocation: Service preferred location.,
        # PreferredNeighbour: Service preferred neighbour.,
        # PreferredDay: Service preferred day.,
        # NoNeighbourDelivery: 	Invoke service No Neighbour Delivery.,
        # NamedPersonOnly: Invoke service Named Person Only.,
        # ReturnReceipt: Invoke service return receipt.,
        # Premium: Premium for fast and safe delivery of international shipments.,
        # CashOnDelivery: Service Cash on delivery.,
        # AdditionalInsurance: Insure shipment with higher than standard amount.,
        # BulkyGoods: Service to ship bulky goods.,
        # IdentCheck: Service configuration for IdentCheck.,
        # ParcelOutletRouting: Service configuration for ParcelOutletRouting.

        service = self.client.factory.create('ShipmentService')
        if carrier.dhl_de_paket_product_code == 'V53WPAK' and carrier.dhl_de_paket_endorsement_type:
            endorsement = self.client.factory.create('Endorsement')
            service.Endorsement = endorsement
            service.Endorsement._active = 1
            service.Endorsement._type = carrier.dhl_de_paket_endorsement_type

        package = package_details.get('package', False)
        if package and package.dhl_is_bulky:
            bg = self.client.factory.create('BulkyGoods')
            service.BulkyGoods = bg
            service.BulkyGoods._active = 1
        return service

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

    def _get_shipment_details(self, picking, carrier, shipment_item):
        shipping_date = picking.date_done
        if not shipping_date or shipping_date < fields.Datetime.now():
            shipping_date = fields.Datetime.now()
        reference = picking.origin and "%s(%s)" % (picking.name, picking.origin) or picking.name
        shipping_date = shipping_date.date()
        shipmentDetails = self.client.factory.create('ShipmentDetailsTypeType')
        shipmentDetails.product = carrier.dhl_de_paket_product_code
        shipmentDetails.accountNumber = self._get_acc_no(carrier)
        shipmentDetails.customerReference = reference[:35]
        shipmentDetails.costCentre = shipment_item['name']

        shipmentDetails.shipmentDate = shipping_date.strftime(DEFAULT_SERVER_DATE_FORMAT)

        shipmentDetails.ShipmentItem = self.get_shipment_item(shipment_item)
        shipmentDetails.Service = self._get_services(picking, carrier, shipment_item)
        shipmentDetails.Notification = self._get_notifications(picking)
        shipmentDetails.BankData = self._get_bank_data(picking, carrier)
        return shipmentDetails

    def _getNameobj(self, partner):
        partner_name = partner._get_name()
        Name = self.client.factory.create('ns0:NameType')
        Name.name1 = partner_name[:50]
        if partner.parent_id:
            Name.name2 = partner.parent_id.name[:50]
        # company.name2 = None
        #         company.Company = Company
        return Name

    def _split_address(self, address, street_name=False):
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
        # need to remove the top part in the future
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
            nstreet_split = re.findall(r'^(\D+)[\s\.](\d+[\w\s\/-]*)$', address)
            if nstreet_split:
                street_split = list(nstreet_split[0])
                street_number = street_split.pop()
                street_name = ' '.join(street_split)
        if not street_number:
            nstreet_split = re.findall(r'^([\d\-\s]+)\s(\d+[\w\s\/-]*)$', address)
            if nstreet_split:
                street_split = list(nstreet_split[0])
                # street_split.pop()  # 2items,last one is the street abrivations
                street_number = street_split.pop()
                street_name = ' '.join(street_split)
                # street_number = street_split[1]
                # street_name = street_name and street_name + ' '+ street_split[0] or street_split[0]
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
        partner_name = partner._get_name()
        address_dict = {}
        street_name = False
        street_number = False
        careof = False
        if partner.street:
            street_name, street_number = self._split_address(partner.street.strip(), street_name)
        if street_number and street_name:
            if partner.street2:
                careof = partner.street2.strip()
        elif not street_number:
            if partner.street2:
                street_name2, street_number2 = self._split_address(partner.street2.strip(), False)
                if street_name2:
                    careof = street_name
                    street_name = street_name2
                if street_number2:
                    street_number = street_number2
        elif not street_name:
            if partner.street2:
                street_name2, street_number2 = self._split_address(partner.street2.strip(), street_name)
                if street_number2:
                    careof = street_number
                    street_number = street_number2
                if street_name2:
                    street_name = street_name2
        if not street_name:
            raise UserError(
                _("No Street Name\nPlease specify street name and street number for partner: %s" % partner_name))
        address_dict.update(streetName=street_name[:35], careof=None)
        if not street_number:
            raise UserError(_("No Street Number\nPlease add street number  for partner: %s" % partner_name))

        # if not partner.street.isdigit():
        #    raise UserError(_("Street Number must be digit\n
        #    Please enter street number as digit for partner: %s (id: %s)"%(partner_name, partner.id)))

        if len(street_number) > 5:
            raise UserError(
                _("Invalid Street Number\nStreet Number cannot be more than 5 digits for partner: %s" % partner_name))
        address_dict.update(streetNumber=street_number)
        if not careof:
            careof = partner.parent_id and partner.parent_id.name or False
        if careof:
            address_dict.update(careof=careof[:35] or None)
        if not partner.zip:
            raise UserError(_("No Zip\nPlease add zip for partner: %s " % partner_name))
        if not partner.country_id:
            raise UserError(_("No Country\nPlease add country for partner: %s " % partner_name))
        #         address.Zip = self.client.factory.create('ns1:Zip')
        #         address.dispatchingInformation = None
        address_dict.update(zip=partner.zip.strip()[:10])

        if not partner.city:
            raise UserError(_("No City\nPlease add city for partner: %s" % partner_name))
        address_dict.update(city=partner.city.strip()[:35])

        address_dict.update(countryISOCode=partner.country_id.code)
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

        contact = partner._get_name()
        # if partner.child_ids:
        #     contact = partner.child_ids[0]  # Can be changed to configuration
        communication.contactPerson = contact.strip()[:50] or None

        return communication

    def _get_shipper_address(self, partner):
        address_dict = self._get_address_from_partner(partner)
        address = self.client.factory.create('ns0:NativeAddressTypeNew')
        address.streetName = address_dict['streetName']
        address.streetNumber = address_dict['streetNumber']
        address.zip = address_dict['zip']
        address.city = address_dict['city']
        # address.addressAddition = address_dict['careof']
        #         address.countryISOCode = address_dict['countryISOCode']
        address.Origin = self._get_origin_from_partner(partner)
        return address

    def _get_receiver_address(self, partner):
        address_dict = self._get_address_from_partner(partner)
        address = self.client.factory.create('ns0:ReceiverNativeAddressType')
        address.streetName = address_dict['streetName']
        address.streetNumber = address_dict['streetNumber']
        address.zip = address_dict['zip']
        address.city = address_dict['city']
        address.name2 = address_dict['careof']
        #         address.countryISOCode = address_dict['countryISOCode']
        address.Origin = self._get_origin_from_partner(partner)
        return address

    def _get_shipper(self, picking, carrier):
        shipper = self.client.factory.create('ShipperType')
        shipper_partner = picking.picking_type_id and picking.picking_type_id.warehouse_id.partner_id
        if not shipper_partner:
            shipper_partner = picking.company_id.partner_id
        shipper.Name = self._getNameobj(shipper_partner)
        shipper.Address = self._get_shipper_address(shipper_partner)
        shipper.Communication = self._get_communication(shipper_partner)
        # shipper.VAT = None
        # shipper.Remark = None
        return shipper

    def _get_receiver_packstation(self, partner):
        packstation = self.client.factory.create('ns0:PackStationType')
        packstation_details = "%s %s" % (partner.street.lower(), partner.street2.lower())
        packstation_details = packstation_details.replace('packstation', '').replace('\n', '').replace('  ', '')
        postnumber, packstationnumber = packstation_details.strip().split(' ')
        # postnumber = [num for num in partner.street.split() if num.isdigit()][-1]
        # packstationnumber = partner.street2.split()[-1]
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
            receiver.Address = self._get_receiver_address(partner)

        return receiver

    def _get_receiver(self, picking, carrier):
        receiver = self.client.factory.create('ReceiverType')
        partner = picking.partner_id
        receiver.name1 = partner._get_name()[:50]
        receiver.Communication = self._get_communication(partner)

        #         receiver.Company.Person = self._get_receiver_person(partner)
        receiver = self.update_receiver_address_packstation(receiver, partner)
        #         receiver.Address = self._get_receiver_address(partner)
        #         receiver.Communication = self._get_receiver_communication(partner)
        # receiver.VAT = None
        # receiver.CompanyName3 = None
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

    def _get_shipment(self, picking, carrier, shipment_item):
        shipment = self.client.factory.create('Shipment')
        shipment.ShipmentDetails = self._get_shipment_details(picking, carrier, shipment_item)
        shipment.Shipper = self._get_shipper(picking, carrier)
        shipment.Receiver = self._get_receiver(picking, carrier)
        shipment.ReturnReceiver = self._get_shipper(picking, carrier)
        shipment.ExportDocument = self._get_export_document(picking, carrier)
        #         shipment.Identity = self._get_identity(picking, carrier)
        #         shipment.FurtherAddresses = self._get_further_addresses(picking, carrier)
        return shipment

    def _get_shipment_order(self, picking, carrier):
        result = []
        shipment_items = self._get_shipment_items(picking, carrier)
        for index, shipment_item in enumerate(shipment_items):

            shipmentOrder = self.client.factory.create('ShipmentOrderType')
            shipmentOrder.sequenceNumber = index
            shipmentOrder.Shipment = self._get_shipment(picking, carrier, shipment_item)
            #         shipmentOrder.Pickup = self._getPickup()

            # shipmentOrder.labelResponseType = 'B64'
            shipmentOrder.PrintOnlyIfCodeable = None
            result.append(shipmentOrder)
        return result

    def _get_shipment_orders(self, picking, carrier):
        shipmentOrders = self._get_shipment_order(picking, carrier)
        return shipmentOrders

    def validate_shipping(self, picking, carrier):
        version = self._get_version()
        shipmentorders = self._get_shipment_orders(picking, carrier)
        response = self.client.service.validateShipment(version, shipmentorders)
        return response

    def create_shipment(self, picking, carrier):
        version = self._get_version()
        shipmentOrders = self._get_shipment_orders(picking, carrier)
        labelresponsetype = carrier.dhl_de_paket_label_response_type or 'B64' # URL,    B64,    ZPL2
        labelformat = carrier.dhl_de_paket_label_format or 'A4'
        # groupProfileName
        # labelFormat
        # labelFormatRetoure
        # combinedPrinting
        #createShipmentOrder(Version Version, ShipmentOrderType[] ShipmentOrder, labelResponseType labelResponseType,
        # xs:string groupProfileName, xs:string labelFormat, xs:string labelFormatRetoure, xs:string combinedPrinting)
        response = self.client.service.createShipmentOrder(version, shipmentOrders,
                                                           labelResponseType=labelresponsetype,
                                                           labelFormat=labelformat)
        return response

    def send_shipping(self, picking, carrier):
        return self.create_shipment(picking, carrier)

    def delete_shipment(self, picking, carrier):
        version = self._get_version()
        shipmentNumber = picking.carrier_tracking_ref.split(',')
        response = self.client.service.deleteShipmentOrder(version, shipmentNumber)
        return response

    def send_cancelling(self, picking, carrier):
        dict_response = {'carrier_tracking_ref': 0.0, 'price': 0.0, 'currency': False}
        return dict_response

    def _remove_accents(self, input_str):
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        only_ascii = nfkd_form.encode('ASCII', 'ignore')
        return only_ascii
