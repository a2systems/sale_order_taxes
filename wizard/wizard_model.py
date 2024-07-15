# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _, Command
from odoo.exceptions import ValidationError

class SaleOrderTaxesWizard(models.TransientModel):
    _name = 'sale.order.taxes.wizard'
    _description = 'sale.order.taxes.wizard'

    order_id = fields.Many2one('sale.order', required=True)
    company_id = fields.Many2one(related='order_id.company_id')
    tax_line_ids = fields.One2many(comodel_name='sale.order.taxes.line.wizard', inverse_name='wizard_id')

    def action_update_tax(self):
        for tax in self.order_id.tax_ids:
            tax.unlink()
        for line in self.tax_line_ids:
            vals = {
                    'order_id': self.order_id.id,
                    'tax_id': line.tax_id.id,
                    'amount': line.amount,
                    }
            line_id = self.env['sale.order.taxes'].create(vals)


    def add_tax_and_new(self):
        self.add_tax()
        return {'type': 'ir.actions.act_window',
                'name': _('Edit tax lines'),
                'res_model': self._name,
                'target': 'new',
                'view_mode': 'form',
                'context': self._context,
            }


class SaleOrderTaxesLineWizard(models.TransientModel):
    _name = 'sale.order.taxes.line.wizard'
    _description = 'sale.order.taxes.line.wizard'

    wizard_id = fields.Many2one('sale.order.taxes.wizard')
    tax_id = fields.Many2one('account.tax', required=True)
    amount = fields.Float()
    new_tax = fields.Boolean(default=True)

    def _get_amount_updated_values(self):
        debit = credit = 0
        if self.invoice_tax_id.move_id.move_type == "in_invoice":
            if self.amount > 0:
                debit = self.amount
            elif self.amount < 0:
                credit = -self.amount
        else:  # For refund
            if self.amount > 0:
                credit = self.amount
            elif self.amount < 0:
                debit = -self.amount

        # If multi currency enable
        move_currency = self.invoice_tax_id.move_id.currency_id
        company_currency = self.invoice_tax_id.move_id.company_currency_id
        if move_currency and move_currency != company_currency:
            return {'amount_currency': self.amount if debit else -self.amount}
        return {'debit': debit, 'credit': credit, 'balance': self.amount if debit else -self.amount}
