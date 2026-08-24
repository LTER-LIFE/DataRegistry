"""Maintainer review of canonical dataset records."""

from flask import flash, redirect, request, session, url_for
from flask import current_app as app
from flask_admin import Admin
from flask_admin.actions import action
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import SecureForm

from application.authentication import in_editor_group
from application.database import db_session
from application.models import (
    DATASET_STATUS_ACCEPTED,
    DATASET_STATUS_REJECTED,
    DATASET_STATUS_REVISION,
    DATASET_STATUS_SUBMITTED,
    Dataset,
)
from application.workflow import transition_dataset


class DatasetReviewAdmin(ModelView):
    can_create = False
    can_delete = True
    can_edit = True
    form_base_class = SecureForm
    form_excluded_columns = (
        "status",
        "submitted_at",
        "accepted_at",
        "submitter_id",
    )
    column_list = (
        "dataset_id",
        "title",
        "status",
        "submitted_at",
        "modified",
        "review_comment",
    )
    column_filters = ("status", "submitted_at", "modified")
    column_searchable_list = ("title", "description", "public_id")

    def is_accessible(self):
        return in_editor_group(session.get("access_token"))

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("main_bp.login", next=request.url))

    def _transition_selected(self, ids, target_status):
        try:
            for dataset_id in ids:
                dataset = self.session.get(Dataset, int(dataset_id))
                if not dataset:
                    raise ValueError(f"Dataset {dataset_id} does not exist.")
                transition_dataset(
                    dataset,
                    target_status,
                    review_comment=dataset.review_comment,
                )
            self.session.commit()
        except ValueError as exc:
            self.session.rollback()
            flash(str(exc), "error")
            return False
        flash(f"Updated {len(ids)} dataset(s) to {target_status}.", "success")
        return True

    @action("accept", "Accept", "Accept selected datasets?")
    def action_accept(self, ids):
        self._transition_selected(ids, DATASET_STATUS_ACCEPTED)

    @action("request_revision", "Request revision", "Request revisions?")
    def action_request_revision(self, ids):
        self._transition_selected(ids, DATASET_STATUS_REVISION)

    @action("reject", "Reject", "Reject selected datasets?")
    def action_reject(self, ids):
        self._transition_selected(ids, DATASET_STATUS_REJECTED)

    @action("resubmit", "Resubmit", "Return selected revisions to review?")
    def action_resubmit(self, ids):
        self._transition_selected(ids, DATASET_STATUS_SUBMITTED)


admin = Admin(app, name="Dataset review")
admin.add_view(DatasetReviewAdmin(Dataset, db_session, category="Catalogue"))
