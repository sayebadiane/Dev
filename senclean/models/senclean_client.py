from odoo import models, fields, api, _


class SencleanClient(models.Model):
    _name = 'senclean.client'
    _description = 'Client SenClean'
    _inherit = ['mail.thread']
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string='Nom complet', required=True, tracking=True)
    phone = fields.Char(string='Téléphone', required=True, tracking=True)
    email = fields.Char(string='Email', required=True, tracking=True)
    address = fields.Char(string='Adresse')
    city = fields.Char(string='Ville', default='Dakar')

    partner_id = fields.Many2one(
        'res.partner', string='Contact Odoo', ondelete='set null', readonly=True
    )
    user_id = fields.Many2one(
        'res.users', string='Compte portail', ondelete='set null', readonly=True
    )

    registration_date = fields.Date(
        string="Date d'inscription", default=fields.Date.today, readonly=True
    )
    state = fields.Selection([
        ('active', 'Actif'),
        ('blocked', 'Bloqué'),
    ], string='Statut', default='active', required=True, tracking=True)

    mission_count = fields.Integer(
        string='Nb missions', compute='_compute_mission_count'
    )

    def _compute_mission_count(self):
        Mission = self.env['senclean.mission']
        for rec in self:
            rec.mission_count = Mission.search_count(
                [('client_id', '=', rec.partner_id.id)]
            ) if rec.partner_id else 0

    @api.model
    def _create_from_portal_signup(self, name, phone, email, address, city, partner):
        """Appelé après l'inscription portail pour créer le profil client."""
        # Éviter les doublons si le client s'est déjà inscrit
        existing = self.search([('partner_id', '=', partner.id)], limit=1)
        if existing:
            return existing

        user = self.env['res.users'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1
        )
        return self.create({
            'name': name,
            'phone': phone,
            'email': email,
            'address': address or '',
            'city': city or 'Dakar',
            'partner_id': partner.id,
            'user_id': user.id if user else False,
        })
