<?xml version="1.0" encoding="utf-8"?>
 <odoo>
 	<data>
    <!-- Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) -->
  	<!-- See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details. -->
 		<record id="view_action_generate_label" model="ir.ui.view">
            <field name="name">Generate Label</field>
            <field name="model">wk.stock.picking.wizard</field>
            <field name="arch" type="xml">
                <form string="Create invoices">
                    <separator colspan="4" string="Do you really want to Genrate the Labels(s)?" />
                    <group>
                    </group>
                    <footer>
                        <h3>For <field name='picking_count'/>Shipment  the label will Generated .</h3>
                        <button name="generate_shipment_label" string="Genrate the Labels" type="object" class="oe_highlight"/>
                        or
                        <button string="Cancel" class="oe_link" special="cancel" />
                    </footer>
               </form>
            </field>
        </record>

        <record id="action_generate_label_wk" model="ir.actions.act_window">
            <field name="name">Generate Label</field>
            <field name="type">ir.actions.act_window</field>
            <field name="res_model">wk.stock.picking.wizard</field>
            <field name="view_mode">form</field>
            <field name="view_id" ref="view_action_generate_label"/>
            <field name="target">new</field>
            <field name="multi">True</field>
        </record>
<!--
        <record model="ir.values" id="model_stock_picking_make_label">
            <field name="model_id" ref="odoo_shipping_service_apps.model_stock_picking" />
            <field name="name">Generate Label</field>
            <field name="key2">client_action_multi</field>
            <field name="value" eval="'ir.actions.act_window,' + str(ref('action_generate_label_wk'))" />
            <field name="key">action</field>
            <field name="model">stock.picking</field>
        </record> -->

        <record id="view_action_void_shipment" model="ir.ui.view">
            <field name="name">Void/Cancel Shipment</field>
            <field name="model">wk.stock.picking.wizard</field>
            <field name="arch" type="xml">
                <form string="Void/Cancel the Shipment">
                    <separator colspan="4" string="Do you really want to Void these Shipment?" />
                    <group>
                    </group>
                    <footer>
                         <h3>Total <field name='picking_count'/>Shipment will Canceled after this action.</h3>
                        <button name="void_shipment" string="Void/Cancel the Shipment" type="object" class="oe_highlight"/>
                        or
                        <button string="Cancel" class="oe_link" special="cancel" />
                    </footer>
               </form>
            </field>
        </record>

        <record id="action_void_shipment_wk" model="ir.actions.act_window">
            <field name="name">Void/Cancel Shipment</field>
            <field name="type">ir.actions.act_window</field>
            <field name="res_model">wk.stock.picking.wizard</field>
            <field name="view_mode">form</field>
            <field name="view_id" ref="view_action_void_shipment"/>
            <field name="target">new</field>
            <field name="multi">True</field>
        </record>

        <!-- <record model="ir.values" id="model_stock_picking_void_shipment">
            <field name="model_id" ref="odoo_shipping_service_apps.model_stock_picking" />
            <field name="name">Void/Cancel Shipment</field>
            <field name="key2">client_action_multi</field>
            <field name="value" eval="'ir.actions.act_window,' + str(ref('action_void_shipment_wk'))" />
            <field name="key">action</field>
            <field name="model">stock.picking</field>
        </record> -->


	</data>
</odoo>
