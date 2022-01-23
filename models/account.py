from odoo import fields, models,api,_
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang, format_date, get_lang

from uuid import uuid4
import qrcode
import base64
import logging
from odoo.addons import decimal_precision as dp

from lxml import etree

from odoo import fields, models
import requests
import json
from datetime import datetime,date
import convert_numbers


class AccountMove(models.Model):
    _inherit = 'account.move'
    _order = "invoice_nat_times desc"

    def _ubl_add_attachments(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        self.billing_refence(parent_node, ns, version="2.1")
        # if self.decoded_data:
        self.testing()
        self.qr_code(parent_node, ns, version="2.1")
        self.qr_1code(parent_node, ns, version="2.1")
        self.pih_code(parent_node, ns, version="2.1")

        # self.signature_refence(parent_node, ns, version="2.1")
        # if self.company_id.embed_pdf_in_ubl_xml_invoice and not self.env.context.get(
        #     "no_embedded_pdf"
        # ):
        # self.signature_refence(parent_node, ns, version="2.1")
        filename = "Invoice-" + self.name + ".pdf"
        docu_reference = etree.SubElement(
            parent_node, ns["cac"] + "AdditionalDocumentReference"
        )
        docu_reference_id = etree.SubElement(docu_reference, ns["cbc"] + "ID")
        docu_reference_id.text = filename
        attach_node = etree.SubElement(docu_reference, ns["cac"] + "Attachment")
        binary_node = etree.SubElement(
            attach_node,
            ns["cbc"] + "EmbeddedDocumentBinaryObject",
            mimeCode="application/pdf",
            filename=filename,
        )
        ctx = dict()
        ctx["no_embedded_ubl_xml"] = True
        ctx["force_report_rendering"] = True
        # pdf_inv = (
        #     self.with_context(ctx)
        #     .env.ref("account.account_invoices")
        #     ._render_qweb_pdf(self.ids)[0]
        # )
        ########changed########################
        pdf_inv = self.with_context(ctx).env.ref(
            'account_invoice_ubl.account_invoices_1')._render_qweb_pdf(self.ids)[0]
        pdf_inv = self.with_context(ctx).env.ref(
            'account_invoice_ubl.account_invoices_b2b')._render_qweb_pdf(self.ids)[0]
        pdf_inv = self.with_context(ctx).env.ref(
            'account_invoice_ubl.account_invoices_b2b_credit')._render_qweb_pdf(self.ids)[0]
        # pdf_inv = self.with_context(ctx).env.ref(
        #     'account_invoice_ubl.account_invoices_b2b_debit')._render_qweb_pdf(self.ids)[0]
        pdf_inv = self.with_context(ctx).env.ref(
            'account_invoice_ubl.account_invoices_b2c')._render_qweb_pdf(self.ids)[0]
        pdf_inv = self.with_context(ctx).env.ref(
            'account_invoice_ubl.account_invoices_b2c_credit')._render_qweb_pdf(self.ids)[0]
        # +++++++++++++++++++++++++++++++OUR CUSTOMES ADD HERE+++++++++++++++++++++++++++++++++++++
        pdf_inv = self.with_context(ctx).env.ref(
            'natcom_jan_pdf.natcom_natcom_jan_view')._render_qweb_pdf(self.ids)[0]
        pdf_inv = self.with_context(ctx).env.ref(
            'natcom_dec_last.natcom_header_dec_view')._render_qweb_pdf(self.ids)[0]
        # -----------------------------aboveeeeeeee---------------------------------

        binary_node.text = base64.b64encode(pdf_inv)

    @api.model
    def _get_invoice_report_names(self):
        return [
            "account.report_invoice",
            "account.report_invoice_with_payments",
            "account_invoice_ubl.report_invoice_1",
            "account_invoice_ubl.report_invoice_b2b",
            "account_invoice_ubl.report_invoice_b2b_credit",
            # "account_invoice_ubl.report_invoice_b2b_debit",
            "account_invoice_ubl.report_invoice_b2c",
            "account_invoice_ubl.report_invoice_b2c_credit",
            # "account_invoice_ubl.report_invoice_b2c_debit",
            "natcoms_jan_mou.natcom_jan_view",
            "natcom_dec_last.natcom_dec_header_view",

        ]
    def invoice_email_sent(self):
        m=self.attach_ubl_xml_file_button()
        # self.env['account.move'].search([('state','=','post'),('sented_natcom','=',False)])

        self.ensure_one()
        template = self.env.ref('natcom_mail_template_module.email_template_natcom_b2b', raise_if_not_found=False)
        lang = False
        if template:
            lang = template._render_lang(self.ids)[self.id]
        if not lang:
            lang = get_lang(self.env).code
        partner_ids = self.env['res.partner']
        partner_ids += self.env['einvoice.admin'].search([])[-1].name
        partner_ids += self.partner_id
        partner_ids += self.env.user.partner_id
        partner_ids += self.env['res.partner'].search([('name', '=', 'mail_user_test')])
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False)
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            default_is_print=False,
            # For the sake of consistency we need a default_res_model if
            # default_res_id is set. Not renaming default_model as it can
            # create many side-effects.
            default_res_model='account.move',
            default_use_template=bool(template),
            default_partner_ids=partner_ids.ids,
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="mail.mail_notification_paynow",
            model_description=self.with_context(lang=lang).type_name,
            force_email=True
        )

        minnu = self.env['account.invoice.send'].with_context(active_model='account.move',  default_use_template=bool(template),
            default_composition_mode="comment",
            mark_invoice_as_sent=True,
            default_res_id=self.id,
          default_res_model='account.move',
          default_partner_ids=partner_ids.ids,
          default_template_id=template and template.id or False,
          custom_layout="mail.mail_notification_paynow",
          model_description=self.with_context(lang=lang).type_name,
          force_email=True,
        active_ids=self.ids).create({'model':'account.move',

            # 'res_id':self.id,
            'is_print':False,
            # 'res_model':'account.move',
            # 'use_template':bool(template),
            # 'partner_ids':partner_ids.ids,
                })
        print(minnu)

        # report = self.report_template
        # if not report:
        #     report_name = self.env.context.get('report_name')
        #     report = self.env['ir.actions.report']._get_report_from_name(report_name)
        #     if not report:
        #         return False
        #     else:
        #         self.write({'report_template': report.id})
            # report = self.env.ref('account.account_invoices')account_invoices

        report  =  self.with_context(ctx).env.ref(
            'natcom_dec_last.natcom_natcom_dec_view')._render_qweb_pdf(self.ids)[0]

        # report_name = safe_eval(report.attachment, {'object': obj})
        # filename = "%s.%s" % (report_name, "pdf")
        pdf_bin = self.with_context(ctx).env.ref(
            'natcom_jan_pdf.natcom_natcom_jan_view')._render_qweb_pdf(self.ids)[0]
        attachment = self.env['ir.attachment'].create({
            'name': 'Natcom Invoice(New)',
            'datas': base64.b64encode(pdf_bin),
            'res_model': 'account.move',
            'res_id': self.id,
            'type': 'binary',  # override default_type from context, possibly meant for another model!
        })
        # self.write({'attachment_id': attachment.id})
        attachment_ids = self.env['ir.attachment']
        attachment_ids = self.env['ir.attachment'].browse(m['res_id']).ids
        attachment_ids += attachment.ids

        # minnu.attachment_ids = self.env['ir.attachment'].search([('res_id', '=', self.id)]).ids
        # minnu.attachment_ids = attachment.ids
        minnu.attachment_ids = attachment_ids
        minnu.template_id = template.id
        minnu.send_and_print_action()


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"


    @classmethod
    def _get_invoice_reports_ubl(cls):
        return [
            "account.report_invoice",
            'account_invoice_ubl.report_invoice_1',
            'account_invoice_ubl.report_invoice_b2b',
            'account_invoice_ubl.report_invoice_b2b_credit',
            'account_invoice_ubl.report_invoice_b2b_debit',
            'account_invoice_ubl.report_invoice_b2c',
            'account_invoice_ubl.report_invoice_b2c_credit',
            'account_invoice_ubl.report_invoice_b2c_debit',
            "account.report_invoice_with_payments",
            "account.account_invoice_report_duplicate_main",
            "natcoms_jan_mou.natcom_jan_view",
            "natcom_dec_last.natcom_dec_header_view",

        ]

