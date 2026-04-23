from odoo import models, fields, api
from datetime import date


class SchoolDashboard(models.TransientModel):
    _name = 'school.dashboard'
    _description = 'Tableau de bord scolaire'

    # Statistiques élèves
    total_students = fields.Integer('Total élèves actifs', compute='_compute_stats')
    total_boys = fields.Integer('Garçons', compute='_compute_stats')
    total_girls = fields.Integer('Filles', compute='_compute_stats')

    # Statistiques classes
    total_classes = fields.Integer('Classes actives', compute='_compute_stats')

    # Statistiques paiements du mois courant
    current_month = fields.Char('Mois courant', compute='_compute_stats')
    monthly_due = fields.Float('Montant dû ce mois (FCFA)', compute='_compute_stats')
    monthly_paid = fields.Float('Montant encaissé ce mois (FCFA)', compute='_compute_stats')
    monthly_remaining = fields.Float('Impayés ce mois (FCFA)', compute='_compute_stats')
    paid_count = fields.Integer('Factures payées', compute='_compute_stats')
    partial_count = fields.Integer('Factures partielles', compute='_compute_stats')
    unpaid_count = fields.Integer('Factures impayées', compute='_compute_stats')

    # Taux de présence (7 derniers jours)
    attendance_rate = fields.Float('Taux de présence (%)', compute='_compute_stats')
    total_absences_month = fields.Integer('Absences ce mois', compute='_compute_stats')

    # Bulletins
    total_bulletins = fields.Integer('Bulletins générés', compute='_compute_stats')

    @api.depends()
    def _compute_stats(self):
        today = date.today()
        month = str(today.month).zfill(2)
        year = str(today.year)

        Student = self.env['school.student']
        Class = self.env['school.class']
        Payment = self.env['school.payment']
        Absence = self.env['school.absence']
        Bulletin = self.env['school.bulletin']

        active_students = Student.search([('state', '=', 'active')])
        monthly_payments = Payment.search([('month', '=', month), ('year', '=', year)])

        # Absences du mois
        first_day = today.replace(day=1)
        month_absences = Absence.search([
            ('date', '>=', first_day),
            ('date', '<=', today),
        ])
        absence_records = month_absences
        presence_records = absence_records.filtered(lambda a: a.is_present)
        attendance = (len(presence_records) / len(absence_records) * 100) if absence_records else 0.0

        for rec in self:
            rec.total_students = len(active_students)
            rec.total_boys = len(active_students.filtered(lambda s: s.gender == 'male'))
            rec.total_girls = len(active_students.filtered(lambda s: s.gender == 'female'))
            rec.total_classes = Class.search_count([('active', '=', True)])
            rec.current_month = today.strftime('%B %Y')
            rec.monthly_due = sum(monthly_payments.mapped('amount_due'))
            rec.monthly_paid = sum(monthly_payments.mapped('amount_paid'))
            rec.monthly_remaining = sum(monthly_payments.mapped('amount_remaining'))
            rec.paid_count = len(monthly_payments.filtered(lambda p: p.state == 'paid'))
            rec.partial_count = len(monthly_payments.filtered(lambda p: p.state == 'partial'))
            rec.unpaid_count = len(monthly_payments.filtered(lambda p: p.state == 'unpaid'))
            rec.attendance_rate = round(attendance, 1)
            rec.total_absences_month = len(absence_records.filtered(lambda a: not a.is_present))
            rec.total_bulletins = Bulletin.search_count([('school_year', '=', f"{today.year - 1}-{today.year}")])
