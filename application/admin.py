"""
Custom admin views for flask admin to be used in approval

"""
from flask import Flask, redirect, url_for, flash
from flask import current_app as app
from flask_admin import Admin, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.actions import action
from markupsafe import Markup
from datetime import datetime

from application.database import Base, db_session
from application.approval import approve_staged_dataset
 
from application.models import Agent, Keyword, Catalog, Checksum, DataService, Dataset, DataTheme, Distribution, \
    LicenseDocument, MediaType, Location
from application.models import AgentStaging, KeywordStaging, CatalogStaging, ChecksumStaging, DataServiceStaging, DatasetStaging, DataThemeStaging, DistributionStaging, \
    LicenseDocumentStaging, MediaTypeStaging, LocationStaging

class DatasetStagingAdmin(ModelView):
    can_create=False
    can_edit=True
    can_delete=False

    column_list = ["dataset_id", "title", "creator_id","is_approved","description","actions"]
    column_filters = ["is_approved", "creator_id"]
    column_searchable_list = ["dataset_id","title","description"]

    def _actions_formatter(self, context, model, name):
        buttons = []
        if not model.is_approved:
            approve_url = url_for(".approve_view", id=model.dataset_id)
            buttons.append(f'<a class="btn btn-sm btn-success" href="{approve_url}">Approve</a>')
        return Markup("&nbsp;".join(buttons))

    column_formatters = {
        "actions": _actions_formatter,
    }

    
    @expose("/approve/<int:id>")
    def approve_view(self, id):
        entry = self.session.get(DatasetStaging, id)
        if not entry:
            flash("Dataset not found.", "error")
            return redirect(url_for(".index_view"))

        approve_staged_dataset(self.session, entry.dataset_id)
        flash(f"Approved dataset '{entry.title}'.", "success")
        return redirect(url_for(".index_view"))
    """

    """
    @action("approve","Approve Selected","Approve and ingest selected datasets?")
    def action_approve(self,ids):
        for id_ in ids:
            approve_staged_dataset(self.session, id_)
        flash(f"Approved {len(ids)} datasets.")
    

admin = Admin(app, name='Staged Dataset admin')

admin.add_view(ModelView(Dataset, db_session, category="Main database"))

admin.add_view(DatasetStagingAdmin(DatasetStaging, db_session, category="Staging"))

