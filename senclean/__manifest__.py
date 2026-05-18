{
    'name': "SenClean",
    'version': '19.0.1.0.0',
    'summary': 'Marketplace de services ménagers au Sénégal',
    'description': """
        SenClean - Plateforme marketplace de services ménagers
        ========================================================
        - Gestion des prestataires (inscription, vérification, validation)
        - Catégories de services (ménage, babysitting, repassage, etc.)
        - Gestion des missions (réservation, exécution, paiement)
        - Tableau de bord admin (statistiques, modération)
        - Système de notation et avis
    """,
    'author': "SenServices",
    'website': "https://senclean.sn",
    'category': 'Services',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'rating',
        'portal',
        'sale',
        'account',
    ],
    'data': [
        'security/senclean_security.xml',
        'security/ir.model.access.csv',
        'data/senclean_sequence_data.xml',
        'data/senclean_service_category_data.xml',
        'views/senclean_service_category_views.xml',
        'views/senclean_provider_views.xml',
        'views/senclean_mission_views.xml',
        'views/senclean_monthly_billing_views.xml',
        'views/senclean_menu.xml',
        'views/portal_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_frontend': [
            'senclean/static/src/css/tabler-icons.min.css',
            'senclean/static/src/css/portal.css',
        ],
    },
}
