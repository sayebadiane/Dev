# Architecture d'un Module Odoo

## Structure générale

```
mon_module/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── mon_modele.py
├── views/
│   ├── mon_modele_views.xml
│   └── menu_items.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── data/
│   └── data.xml
├── demo/
│   └── demo.xml
├── controllers/
│   ├── __init__.py
│   └── main.py
├── wizard/
│   ├── __init__.py
│   ├── mon_wizard.py
│   └── mon_wizard_views.xml
├── report/
│   ├── mon_rapport.xml
│   └── mon_rapport_template.xml
├── static/
│   └── src/
│       ├── js/
│       ├── scss/
│       ├── components/
│       └── views/
├── tests/
│   ├── __init__.py
│   └── test_mon_modele.py
└── i18n/
    └── fr.po
```

---

## Description des fichiers et dossiers

### `__manifest__.py`
Fichier de déclaration du module. Obligatoire.

```python
{
    'name': 'Mon Module',
    'version': '19.0.1.0.0',
    'summary': 'Description courte',
    'description': 'Description longue',
    'author': 'Mon Nom',
    'website': 'https://monsite.com',
    'category': 'Uncategorized',
    'depends': ['base', 'mail'],        # Dépendances
    'data': [                           # Fichiers chargés en production
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/mon_modele_views.xml',
        'views/menu_items.xml',
        'data/data.xml',
    ],
    'demo': [                           # Fichiers chargés en mode démo
        'demo/demo.xml',
    ],
    'assets': {                         # Assets JS/CSS/SCSS
        'web.assets_backend': [
            'mon_module/static/src/js/**/*',
            'mon_module/static/src/scss/**/*',
        ],
    },
    'installable': True,
    'application': True,                # True si c'est une app principale
    'auto_install': False,
    'license': 'LGPL-3',
}
```

---

### `__init__.py` (racine)
Importe les sous-packages.

```python
from . import models
from . import controllers
from . import wizard
```

---

### `models/`
Contient les classes Python représentant les tables de la base de données.

#### `models/__init__.py`
```python
from . import mon_modele
```

#### `models/mon_modele.py`
```python
from odoo import models, fields, api

class MonModele(models.Model):
    _name = 'mon.modele'               # Nom technique (= nom de la table)
    _description = 'Mon Modèle'
    _inherit = ['mail.thread']         # Héritage de fonctionnalités

    # Champs
    name = fields.Char(string='Nom', required=True)
    date = fields.Date(string='Date')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Terminé'),
    ], default='draft')
    partner_id = fields.Many2one('res.partner', string='Partenaire')
    line_ids = fields.One2many('mon.modele.line', 'parent_id', string='Lignes')

    # Méthodes
    @api.depends('line_ids')
    def _compute_total(self):
        for rec in self:
            rec.total = sum(rec.line_ids.mapped('amount'))

    def action_confirm(self):
        self.state = 'done'
```

**Types de champs courants :**

| Champ | Description |
|---|---|
| `Char` | Texte court |
| `Text` | Texte long |
| `Integer` | Entier |
| `Float` | Décimal |
| `Boolean` | Vrai/Faux |
| `Date` | Date |
| `Datetime` | Date + heure |
| `Selection` | Liste déroulante |
| `Many2one` | Clé étrangère (N→1) |
| `One2many` | Relation inverse (1→N) |
| `Many2many` | Relation N→N |
| `Binary` | Fichier/image |
| `Html` | Contenu HTML |
| `Monetary` | Montant avec devise |

---

### `views/`
Fichiers XML définissant l'interface utilisateur.

#### `views/mon_modele_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!-- Vue liste -->
    <record id="view_mon_modele_tree" model="ir.ui.view">
        <field name="name">mon.modele.tree</field>
        <field name="model">mon.modele</field>
        <field name="arch" type="xml">
            <list>
                <field name="name"/>
                <field name="date"/>
                <field name="state"/>
            </list>
        </field>
    </record>

    <!-- Vue formulaire -->
    <record id="view_mon_modele_form" model="ir.ui.view">
        <field name="name">mon.modele.form</field>
        <field name="model">mon.modele</field>
        <field name="arch" type="xml">
            <form>
                <header>
                    <button name="action_confirm" string="Confirmer" type="object"/>
                    <field name="state" widget="statusbar"/>
                </header>
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="date"/>
                        <field name="partner_id"/>
                    </group>
                    <notebook>
                        <page string="Lignes">
                            <field name="line_ids"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        </field>
    </record>

    <!-- Action -->
    <record id="action_mon_modele" model="ir.actions.act_window">
        <field name="name">Mon Modèle</field>
        <field name="res_model">mon.modele</field>
        <field name="view_mode">list,form</field>
    </record>

</odoo>
```

#### `views/menu_items.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!-- Menu principal -->
    <menuitem id="menu_mon_module_root"
              name="Mon Module"
              sequence="10"/>

    <!-- Sous-menu -->
    <menuitem id="menu_mon_modele"
              name="Mon Modèle"
              parent="menu_mon_module_root"
              action="action_mon_modele"
              sequence="10"/>

</odoo>
```

---

### `security/`

#### `security/ir.model.access.csv`
Définit les droits d'accès CRUD par groupe.

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_mon_modele_user,mon.modele.user,model_mon_modele,base.group_user,1,1,1,0
access_mon_modele_manager,mon.modele.manager,model_mon_modele,base.group_system,1,1,1,1
```

#### `security/security.xml`
Définit les groupes et règles d'accès par enregistrement.

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="module_category_mon_module" model="ir.module.category">
        <field name="name">Mon Module</field>
    </record>

    <record id="group_mon_module_user" model="res.groups">
        <field name="name">Utilisateur</field>
        <field name="category_id" ref="module_category_mon_module"/>
    </record>

    <record id="group_mon_module_manager" model="res.groups">
        <field name="name">Gestionnaire</field>
        <field name="category_id" ref="module_category_mon_module"/>
        <field name="implied_ids" eval="[(4, ref('group_mon_module_user'))]"/>
    </record>
</odoo>
```

---

### `data/`
Données chargées automatiquement à l'installation du module (séquences, paramètres, emails types, etc.).

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="sequence_mon_modele" model="ir.sequence">
        <field name="name">Mon Modèle</field>
        <field name="code">mon.modele</field>
        <field name="prefix">MM/%(year)s/</field>
        <field name="padding">4</field>
    </record>
</odoo>
```

---

### `wizard/`
Boîtes de dialogue temporaires pour des actions ponctuelles.

#### `wizard/mon_wizard.py`
```python
from odoo import models, fields, api

class MonWizard(models.TransientModel):   # TransientModel = temporaire
    _name = 'mon.wizard'
    _description = 'Mon Assistant'

    date = fields.Date(string='Date', required=True)
    note = fields.Text(string='Note')

    def action_valider(self):
        # Logique métier
        return {'type': 'ir.actions.act_window_close'}
```

---

### `controllers/`
Endpoints HTTP pour le frontend (site web, API JSON-RPC, portail).

```python
from odoo import http
from odoo.http import request

class MonController(http.Controller):

    @http.route('/mon-module/liste', auth='public', website=True)
    def liste(self, **kwargs):
        records = request.env['mon.modele'].search([])
        return request.render('mon_module.template_liste', {'records': records})

    @http.route('/mon-module/api/data', auth='user', type='json')
    def get_data(self, **kwargs):
        return {'status': 'ok'}
```

---

### `report/`
Rapports PDF générés via QWeb.

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Déclaration du rapport -->
    <record id="report_mon_modele" model="ir.actions.report">
        <field name="name">Mon Rapport</field>
        <field name="model">mon.modele</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">mon_module.report_mon_modele_template</field>
    </record>

    <!-- Template QWeb -->
    <template id="report_mon_modele_template">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="doc">
                <div class="page">
                    <h1><t t-esc="doc.name"/></h1>
                    <p>Date : <t t-esc="doc.date"/></p>
                </div>
            </t>
        </t>
    </template>
</odoo>
```

---

### `static/src/`
Assets frontend (JavaScript OWL, SCSS, composants).

```
static/src/
├── components/        # Composants OWL réutilisables
│   └── mon_widget/
│       ├── mon_widget.js
│       ├── mon_widget.xml   (template)
│       └── mon_widget.scss
├── views/             # Vues JS personnalisées
├── js/
│   └── tours/         # Tutoriels interactifs
└── scss/              # Styles globaux
```

#### Exemple de composant OWL
```javascript
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

class MonWidget extends Component {
    static template = "mon_module.MonWidget";

    onClick() {
        console.log("Cliqué !");
    }
}

registry.category("fields").add("mon_widget", { component: MonWidget });
```

---

### `tests/`
Tests automatisés.

```python
from odoo.tests.common import TransactionCase

class TestMonModele(TransactionCase):

    def setUp(self):
        super().setUp()
        self.modele = self.env['mon.modele'].create({'name': 'Test'})

    def test_creation(self):
        self.assertEqual(self.modele.state, 'draft')

    def test_confirmation(self):
        self.modele.action_confirm()
        self.assertEqual(self.modele.state, 'done')
```

---

### `i18n/`
Fichiers de traduction `.po` générés par Odoo.

```
i18n/
├── fr.po     # Français
├── ar.po     # Arabe
└── mon_module.pot   # Template de traduction
```

---

## Héritage de modèles

```python
# Étendre un modèle existant sans créer une nouvelle table
class ResPartner(models.Model):
    _inherit = 'res.partner'

    mon_champ = fields.Char(string='Mon Champ')
```

```xml
<!-- Étendre une vue existante -->
<record id="view_partner_form_inherit" model="ir.ui.view">
    <field name="name">res.partner.form.inherit.mon_module</field>
    <field name="model">res.partner</field>
    <field name="inherit_id" ref="base.view_partner_form"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='phone']" position="after">
            <field name="mon_champ"/>
        </xpath>
    </field>
</record>
```

---

## Ordre de chargement des fichiers dans `__manifest__.py`

1. `security/` → droits d'accès (toujours en premier)
2. `data/` → données de référence
3. `views/` → interface utilisateur
4. `wizard/` → assistants
5. `report/` → rapports
6. `demo/` → données de démonstration

---

## Commandes utiles

```bash
# Installer un module
./odoo-bin -d ma_base -i mon_module

# Mettre à jour un module
./odoo-bin -d ma_base -u mon_module

# Lancer les tests d'un module
./odoo-bin -d ma_base --test-enable -i mon_module

# Mettre à jour les traductions
./odoo-bin -d ma_base --i18n-export=mon_module/i18n/fr.po --modules=mon_module --language=fr_FR
```
