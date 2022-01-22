# -*- coding: utf-8 -*-
#################################################################################
##    Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
import pprint
from  collections import defaultdict
def wkodoo_get_product_package(line_info,packaging_info):
    result=[]
    max_qty = packaging_info.get('qty')
    max_weight = packaging_info.get('max_weight')
    dimension=dict(
        height=packaging_info.get('height'),
        width=packaging_info.get('width'),
        length=packaging_info.get('length'),
        packaging_id=packaging_info.get('id'),
        product_id = line_info.get('product_id'),
        line_id =  line_info.get('id'),
    )
    product_qty = line_info.get('product_uom_qty')
    product_weight = line_info.get('product_weight',1)
    package_count=int(product_qty/max_qty)
    if package_count:#Create full capacity package of count int(product_qty/max_qty)
        multi_pckg_max_qty =dimension.copy()
        multi_pckg_max_qty.update(dict(
            weight = product_weight,#*max_qty,
            full_capacity=True,
            qty_capacity=max_qty,
            ))
        result+=[multi_pckg_max_qty]*package_count
    if product_qty%max_qty:#Create rest of half package
        single_pckg_max_qty=dimension.copy()
        single_pckg_max_qty.update(dict(
            weight = product_weight,#*(product_qty%max_qty),
            full_capacity=False,
            qty_capacity=product_qty%max_qty,
            ))
        result+=[single_pckg_max_qty]*1
    return result

def wkodoo_merge_half_package(items,max_qty=10):
    half_items = defaultdict(list)
    for item in filter(lambda item:not item.get('full_capacity'),items):
        product_id = item.get('product_id')
        half_items[product_id].append(item)
    full_items= filter(lambda item:item.get('full_capacity'),items)
    for product_id,packaging_lines in half_items.items():
        p_qty_capacity = sum(map(lambda item:item.get('qty_capacity'),packaging_lines))
        full_package=  p_qty_capacity//max_qty
        half_package =  p_qty_capacity%max_qty
        if full_package:
            temp=packaging_lines[0]
            full_items+=[temp]*int(full_package)
        if half_package:
            temp_lines = map(lambda p:p.get('line_id'),packaging_lines)
            for packaging_line in packaging_lines:
                same_product_half =  filter(lambda item:(not item.get('full_capacity')) and item.get('line_id')!=packaging_line.get('line_id') and item.get('product_id')==product_id  and  item.get('qty_capacity')+packaging_line.get('qty_capacity')<=max_qty ,full_items)
                same_product_half =  sorted(same_product_half, key=lambda x: x.get('qty_capacity'),reverse=False)
                if same_product_half:#Merge two same half product package
                    same_product_half =same_product_half[0]
                    map(lambda i:i.get('line_id')==same_product_half.get('line_id') and full_items.remove(i) ,full_items)
                    same_product_half['qty_capacity']=(same_product_half.get('qty_capacity')+packaging_line.get('qty_capacity'))
                    full_items+=[same_product_half]
                else:
                    full_items+=[packaging_line]
    return full_items
if __name__=='__main__':
    packaging_info={'qty': 10.0, 'width': 10, 'length': 10, 'height': 10, 'id': 1, 'max_weight': 65.0}
    lines=[{'product_uom_qty': 1.0, 'id': 131, 'product_id': (11, u'[E-COM02] iPad Retina Display (16 GB, Black)')}, {'product_uom_qty': 12.0, 'id': 132, 'product_id': (12, u'[E-COM03] iPad Retina Display (32 GB, White)')}]
    lines=[{'product_uom_qty': 1.0, 'id': 133, 'product_id': (11, u'[E-COM02] iPad Retina Display (16 GB, Black)')}, {'product_uom_qty': 12.0, 'id': 134, 'product_id': (12, u'[E-COM03] iPad Retina Display (32 GB, White)')}, {'product_uom_qty': 11.0, 'id': 135, 'product_id': (17, u'[E-COM08] Apple In-Ear Headphones')}]
    lines=[{'product_uom_qty': 10.0, 'id': 132, 'product_id': (11, u'[E-COM02] iPad Retina Display (16 GB, Black)')},
    {'product_uom_qty': 12.0, 'id': 133, 'product_id': (11, u'[E-COM02] iPad Retina Display (16 GB, Black)')},
    {'product_uom_qty': 1.0, 'id': 137 ,'product_id': (11, u'[E-COM02] iPad Retina Display (16 GB, Black)')},
    {'product_uom_qty': 11.0, 'id': 138 ,'product_id': (11, u'[E-COM02] iPad Retina Display (16 GB, Black)')},

    {'product_uom_qty': 12.0, 'id': 134, 'product_id': (12, u'[E-COM03] iPad Retina Display (32 GB, White)')},
    {'product_uom_qty': 13.0, 'id': 135, 'product_id': (17, u'[E-COM08] Apple In-Ear Headphones')},
    {'product_uom_qty': 6.0, 'id': 136, 'product_id': (17, u'[E-COM08] Apple In-Ear Headphones')},
    # {'product_uom_qty': 9.0, 'id': 137, 'product_id': (17, u'[E-COM08] Apple In-Ear Headphones')},
    ]
    res_package =[]
    for line_info in lines:
        res_package.extend(wkodoo_get_product_package(line_info,packaging_info))
    pprint.pprint(res_package)
    pprint.pprint(wkodoo_merge_half_package(res_package))
