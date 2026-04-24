from odoo import models, fields, api, exceptions


class SchoolBulletin(models.Model):
    _name = 'school.bulletin'
    _description = 'Bulletin scolaire'
    _inherit = ['mail.thread']
    _rec_name = 'school_year'   # champ non-calculé ; display_name est surchargé ci-dessous
    _order = 'school_year desc, trimester, student_id'

    student_id = fields.Many2one('school.student', string='Élève', required=True, tracking=True, ondelete='cascade')
    class_id = fields.Many2one('school.class', string='Classe', related='student_id.class_id', store=True)
    school_year = fields.Char('Année scolaire', required=True, default='2024-2025')
    trimester = fields.Selection([
        ('1', '1er Trimestre'),
        ('2', '2ème Trimestre'),
        ('3', '3ème Trimestre'),
    ], string='Trimestre', required=True, tracking=True)
    line_ids = fields.One2many('school.bulletin.line', 'bulletin_id', string='Notes par matière')
    average = fields.Float('Moyenne générale (/20)', compute='_compute_average', store=True, digits=(5, 2))
    rank = fields.Integer('Rang', default=0)
    appreciation = fields.Char('Appréciation', compute='_compute_appreciation', store=True)
    teacher_comment = fields.Text('Appréciation du conseil de classe')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validé'),
    ], string='État', default='draft', tracking=True)

    _sql_constraints = [
        ('unique_student_trimester_year',
         'UNIQUE(student_id, trimester, school_year)',
         'Un seul bulletin par élève, trimestre et année scolaire.'),
    ]

    @api.depends('student_id', 'trimester', 'school_year', 'student_id.name', 'student_id.firstname')
    def _compute_display_name(self):
        trimester_labels = {'1': '1er Trim', '2': '2ème Trim', '3': '3ème Trim'}
        for rec in self:
            rec.display_name = (
                f"{rec.student_id.full_name or ''} - "
                f"{trimester_labels.get(rec.trimester, '')} {rec.school_year}"
            )

    @api.depends('line_ids.weighted_note', 'line_ids.coefficient')
    def _compute_average(self):
        for rec in self:
            total_weighted = sum(rec.line_ids.mapped('weighted_note'))
            total_coeff = sum(rec.line_ids.mapped('coefficient'))
            rec.average = round(total_weighted / total_coeff, 2) if total_coeff > 0 else 0.0

    @api.depends('average')
    def _compute_appreciation(self):
        for rec in self:
            avg = rec.average
            if avg >= 16:
                rec.appreciation = 'Excellent'
            elif avg >= 14:
                rec.appreciation = 'Très bien'
            elif avg >= 12:
                rec.appreciation = 'Bien'
            elif avg >= 10:
                rec.appreciation = 'Assez bien'
            elif avg >= 8:
                rec.appreciation = 'Insuffisant'
            else:
                rec.appreciation = 'Très insuffisant'

    def action_validate(self):
        for rec in self:
            if not rec.line_ids:
                raise exceptions.UserError("Aucune note n'a été saisie pour ce bulletin.")
            rec.state = 'validated'

    def action_draft(self):
        self.state = 'draft'

    def action_print_bulletin(self):
        return self.env.ref('school_management.action_report_bulletin').report_action(self)

    def action_compute_ranks(self):
        """Recalcule les rangs pour tous les bulletins de la même classe/trimestre/année."""
        domain = [
            ('class_id', '=', self.class_id.id),
            ('trimester', '=', self.trimester),
            ('school_year', '=', self.school_year),
        ]
        bulletins = self.search(domain).sorted(key=lambda r: r.average, reverse=True)
        for rank, bulletin in enumerate(bulletins, start=1):
            bulletin.rank = rank
        return True


class SchoolBulletinLine(models.Model):
    _name = 'school.bulletin.line'
    _description = 'Note par matière'
    _order = 'subject_id'

    bulletin_id = fields.Many2one('school.bulletin', string='Bulletin', required=True, ondelete='cascade')
    subject_id = fields.Many2one('school.subject', string='Matière', required=True)
    note = fields.Float('Note (/20)', digits=(5, 2))
    coefficient = fields.Float('Coefficient', default=1.0)
    weighted_note = fields.Float('Note pondérée', compute='_compute_weighted', store=True)
    teacher_comment = fields.Char('Appréciation du professeur')

    @api.constrains('note')
    def _check_note(self):
        for rec in self:
            if not (0 <= rec.note <= 20):
                raise exceptions.ValidationError("La note doit être comprise entre 0 et 20.")

    @api.depends('note', 'coefficient')
    def _compute_weighted(self):
        for rec in self:
            rec.weighted_note = rec.note * rec.coefficient

    @api.onchange('subject_id')
    def _onchange_subject(self):
        if self.subject_id:
            self.coefficient = self.subject_id.coefficient
