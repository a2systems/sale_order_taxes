# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unicodedata import name
from dateutil.relativedelta import relativedelta
from datetime import date,datetime,timedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import ValidationError

class SaleOrderTaxes(models.Model):
    _name = 'sale.order.taxes'
    _description = 'sale.order.taxes'

    order_id = fields.Many2one('sale.order',string='Pedido')
    tax_id = fields.Many2one('account.tax','Impuesto')
    amount = fields.Float('Monto')

    def _get_amount_updated_values(self):
        debit = credit = 0
        credit = self.amount

        # If multi currency enable
        move_currency = self.order_id.pricelist_id.currency_id
        company_currency = self.order_id.company_id.currency_id
        vals = {'debit': debit, 'credit': credit, 'balance': -self.amount}
        if move_currency and move_currency.id != company_currency.id:
            vals['amount_currency'] = -self.amount 
        return vals
