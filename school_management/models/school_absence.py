from odoo import models, fields, api, exceptions
from datetime import date


class SchoolAbsence(models.Model):
    _name = 'school.absence'
    _description = 'Présence / Absence'
    _order = 'date desc, student_id'

    student_id = fields.Many2one('school.student', string='Élève', required=True, ondelete='cascade')
    class_id = fields.Many2one('school.class', string='Classe', related='student_id.class_id', store=True)
    date = fields.Date('Date', required=True, default=fields.Date.today)
    is_present = fields.Boolean('Présent', default=False)
    reason = fields.Selection([
        ('sick', 'Maladie'),
        ('appointment', 'Rendez-vous médical'),
        ('family', 'Raison familiale'),
        ('unjustified', 'Absence injustifiée'),
        ('other', 'Autre'),
    ], string='Motif')
    note = fields.Text('Observation')
    justified = fields.Boolean('Justifiée', compute='_compute_justified', store=True)

    _sql_constraints = [
        ('unique_student_date', 'UNIQUE(student_id, date)', 'Un seul enregistrement de présence par élève et par jour.'),
    ]

    @api.depends('is_present', 'reason')
    def _compute_justified(self):
        justified_reasons = {'sick', 'appointment', 'family'}
        for rec in self:
            if rec.is_present:
                rec.justified = True
            else:
                rec.justified = rec.reason in justified_reasons

    @api.constrains('date')
    def _check_date(self):
        for rec in self:
            if rec.date and rec.date > date.today():
                raise exceptions.ValidationError("La date ne peut pas être dans le futur.")

    @api.model
    def mark_class_attendance(self, class_id, attendance_date, records):
        """
        records: list of dict {'student_id': int, 'is_present': bool, 'reason': str}
        """
        for record in records:
            existing = self.search([
                ('student_id', '=', record['student_id']),
                ('date', '=', attendance_date),
            ], limit=1)
            vals = {
                'student_id': record['student_id'],
                'date': attendance_date,
                'is_present': record.get('is_present', False),
                'reason': record.get('reason', False),
            }
            if existing:
                existing.write(vals)
            else:
                self.create(vals)
