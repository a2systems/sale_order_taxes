# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unicodedata import name
from dateutil.relativedelta import relativedelta
from datetime import date,datetime,timedelta

from odoo import api, fields, models, SUPERUSER_ID, _, Command
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tax_ids = fields.One2many(comodel_name='sale.order.taxes',inverse_name='order_id',string='Impuestos') 

    def btn_add_taxes(self):
        self.ensure_one()
        if self.state not in ['draft','sent']:
            raise ValidationError('Solo se pueden agregar/modificar impuestos en movimientos en borrador')
        if not self.order_line:
            raise ValidationError('Debe ingresar al menos una línea')
        vals = {
            'order_id': self.id,
            }
        wizard_id = self.env['sale.order.taxes.wizard'].create(vals)
        for line in self.order_line.filtered(lambda x: x.tax_id):
            for tax in line.tax_id:
                vals_line = {
                    'wizard_id': wizard_id.id,
                    'tax_id': line.tax_id.id,
                    'amount': line.price_tax,
                    'new_tax': False,
                    }
                line_id = self.env['sale.order.taxes.line.wizard'].create(vals_line)
        for perception in self.partner_id.perception_ids:
            amount = self.amount_untaxed * perception.percent / 100 
            vals_line = {
                    'wizard_id': wizard_id.id,
                    'tax_id': perception.tax_id.id,
                    'amount': amount,
                    'new_tax': True,
                    }
            line_id = self.env['sale.order.taxes.line.wizard'].search([('wizard_id','=',wizard_id.id),('tax_id','=',perception.tax_id.id)])
            if not line_id:
                line_id = self.env['sale.order.taxes.line.wizard'].create(vals_line)
        if self.partner_shipping_id:
            for perception in self.partner_shipping_id.perception_ids:
                amount = self.amount_untaxed * perception.percent / 100 
                vals_line = {
                    'wizard_id': wizard_id.id,
                    'tax_id': perception.tax_id.id,
                    'amount': amount,
                    'new_tax': True,
                    }
            line_id = self.env['sale.order.taxes.line.wizard'].search([('wizard_id','=',wizard_id.id),('tax_id','=',perception.tax_id.id)])
            if not line_id:
                line_id = self.env['sale.order.taxes.line.wizard'].create(vals_line)
        res = {
            'name': _('Sale Order Taxes Wizard'),
            'res_model': 'sale.order.taxes.wizard',
            'view_mode': 'form',
            'res_id': wizard_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        return res


    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total','tax_ids')
    def _compute_amounts(self):
        """Compute the total amounts of the SO."""
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))

            if order.tax_ids:
                for tax_line in order.tax_ids:
                    if tax_line.tax_id.tax_group_id.tax_type == 'withholdings':
                        amount_tax = amount_tax + tax_line.amount

            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = order.amount_untaxed + order.amount_tax

    def _create_invoices(self, grouped=False, final=False, date=None):
        res = super(SaleOrder, self)._create_invoices(grouped=grouped, final=final, date=date)
        for rec in self:
            to_add_tax = self.env['account.tax']
            for tax_line in rec.tax_ids:
                if tax_line.tax_id.tax_group_id.tax_type == 'withholdings':
                    to_add_tax += tax_line.tax_id
            if to_add_tax:
                for move in res:
                    container = {'records':move, 'self':move}
                    with move.with_context(check_move_validity=False)._check_balanced(container):
                        with move._sync_dynamic_lines(container):
                            move.invoice_line_ids.filtered(lambda x: x.display_type == 'product').write({'tax_ids': [Command.link(tax_id.id) for tax_id in to_add_tax]})
                    container = {'records': move}
                    with move._check_balanced(container):
                        with move._sync_dynamic_lines(container):
                            # restauramos todos los valores de impuestos fixed que se habrian recomputado
                            #restaured = []
                            for tax_line_id in rec.tax_ids.filtered(lambda l: l.tax_id.tax_group_id.tax_type == 'withholdings'):
                                # seteamos valor al impuesto segun lo que puso en el wizard
                                line_with_tax = move.line_ids.filtered(lambda x: x.tax_line_id == tax_line_id.tax_id)
                                vals = tax_line_id._get_amount_updated_values()
                                line_with_tax.write(vals)

        return res
