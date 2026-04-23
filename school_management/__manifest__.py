{
    'name': "Gestion École Privée",
    'version': '19.0.1.0.0',
    'summary': 'Application complète de gestion scolaire',
    'description': """
        Module de gestion d'école privée :
        - Tableau de bord avec statistiques
        - Gestion des élèves
        - Gestion des classes
        - Paiements de scolarité
        - Gestion des absences
        - Bulletins scolaires
        - Gestion des parents
        - Rapports PDF
    """,
    'author': 'UnikerP',
    'website': 'https://www.unikerp.com',
    'category': 'Education',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/school_security.xml',
        'security/ir.model.access.csv',
        'data/school_data.xml',
        # Toutes les vues qui définissent des actions en premier
        'views/school_student_views.xml',
        'views/school_class_views.xml',
        'views/school_payment_views.xml',
        'views/school_absence_views.xml',
        'views/school_bulletin_views.xml',
        'views/school_parent_views.xml',
        'views/school_subject_views.xml',
        # Dashboard en dernier : ses boutons référencent les actions ci-dessus
        'views/school_dashboard_views.xml',
        'views/menus.xml',
        'reports/school_bulletin_report.xml',
        'reports/school_payment_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'school_management/static/src/css/school_dashboard.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
