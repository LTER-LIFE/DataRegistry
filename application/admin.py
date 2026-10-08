"""Maintainer review of canonical dataset records."""

import logging

from flask import abort, current_app, flash, redirect, request, session, url_for
from flask_admin import Admin, expose
from flask_admin.actions import action
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import SecureForm
from flask_admin.helpers import get_form_data
from flask_admin.model.template import EndpointLinkRowAction
from sqlalchemy.orm import selectinload
from wtforms import SelectField, TextAreaField
from wtforms.validators import DataRequired, Optional

from application.authentication import has_editor_access, oidc_subject
from application.database import db_session
from application.models import (
    Dataset,
    ReviewLifecycle,
    REVIEW_ACTOR_AUTHENTICATED,
    REVIEW_ACTOR_LOCAL_BYPASS,
    REVIEW_STATUS_ACCEPTED,
    REVIEW_STATUS_REJECTED,
    REVIEW_STATUS_REVISION,
    REVIEW_STATUS_SUBMITTED,
)
from application.workflow import ALLOWED_TRANSITIONS, transition_reviewable


class ReviewTransitionForm(SecureForm):
    target_status = SelectField("Target status", validators=[DataRequired()])
    review_comment = TextAreaField("Review comment", validators=[Optional()])


class DatasetReviewAdmin(ModelView):
    can_create = False
    can_delete = True
    can_edit = True
    form_base_class = SecureForm
    form_excluded_columns = (
        "review_lifecycle",
        "review_lifecycle_id",
        "review_owner_type",
        "modified",
    )
    column_list = (
        "dataset_id",
        "title",
        "review_lifecycle.status",
        "review_lifecycle.submitted_at",
        "modified",
        "review_lifecycle.current_review_comment",
    )
    column_labels = {
        "review_lifecycle.status": "Status",
        "review_lifecycle.submitted_at": "Submitted",
        "review_lifecycle.current_review_comment": "Review feedback",
    }
    column_choices = {
        "review_lifecycle.status": (
            (REVIEW_STATUS_SUBMITTED, "Submitted"),
            (REVIEW_STATUS_REVISION, "Revision"),
            (REVIEW_STATUS_REJECTED, "Rejected"),
            (REVIEW_STATUS_ACCEPTED, "Accepted"),
        ),
    }
    column_filters = (
        "review_lifecycle.status",
        "review_lifecycle.submitted_at",
        "modified",
    )
    column_select_related_list = (Dataset.review_lifecycle,)
    column_extra_row_actions = [
        EndpointLinkRowAction("fa fa-eye", ".review_view", title="Review"),
    ]
    column_searchable_list = ("title", "description", "public_id")

    def is_accessible(self):
        return has_editor_access(session.get("access_token"))

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("main_bp.login", next=request.url))

    @staticmethod
    def _review_actor():
        if current_app.config.get("LOCAL_EDITOR_BYPASS", False):
            return None, REVIEW_ACTOR_LOCAL_BYPASS
        actor_id = oidc_subject(session.get("access_token"))
        if not actor_id:
            raise ValueError("Authenticated review activity requires an actor identity.")
        return actor_id, REVIEW_ACTOR_AUTHENTICATED

    def _transition_selected(self, ids, target_status, review_comment=None):
        try:
            actor_id, actor_mode = self._review_actor()
            for dataset_id in sorted(int(value) for value in ids):
                dataset = self.session.get(Dataset, dataset_id)
                if not dataset:
                    raise ValueError(f"Dataset {dataset_id} does not exist.")
                transition_reviewable(
                    dataset,
                    target_status,
                    review_comment=review_comment,
                    actor_id=actor_id,
                    actor_mode=actor_mode,
                )
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            if not isinstance(exc, ValueError):
                logging.exception("Failed to transition dataset lifecycle.")
            flash(str(exc), "error")
            return False
        flash(f"Updated {len(ids)} dataset(s) to {target_status}.", "success")
        return True

    def delete_model(self, model):
        """Delete the complete lifecycle aggregate rather than its owner row."""
        try:
            self.on_model_delete(model)
            self.session.flush()
            self.session.delete(model.review_lifecycle)
            self.session.commit()
        except Exception as exc:
            if not self.handle_view_exception(exc):
                flash(f"Failed to delete record. {exc}", "error")
                logging.exception("Failed to delete dataset lifecycle.")
            self.session.rollback()
            return False
        self.after_model_delete(model)
        return True

    @expose("/review/<int:id>/", methods=("GET", "POST"))
    def review_view(self, id):
        dataset = (
            self.session.query(Dataset)
            .options(
                selectinload(Dataset.review_lifecycle).selectinload(
                    ReviewLifecycle.transitions
                )
            )
            .filter(Dataset.dataset_id == id)
            .one_or_none()
        )
        if dataset is None:
            abort(404)

        lifecycle = dataset.review_lifecycle
        status_order = (
            REVIEW_STATUS_SUBMITTED,
            REVIEW_STATUS_REVISION,
            REVIEW_STATUS_REJECTED,
            REVIEW_STATUS_ACCEPTED,
        )
        allowed = ALLOWED_TRANSITIONS.get(lifecycle.status, set())
        form = ReviewTransitionForm(get_form_data())
        form.target_status.choices = [
            (status, status.replace("_", " ").title())
            for status in status_order
            if status in allowed
        ]

        if self.validate_form(form):
            try:
                actor_id, actor_mode = self._review_actor()
                transition_reviewable(
                    dataset,
                    form.target_status.data,
                    review_comment=form.review_comment.data,
                    actor_id=actor_id,
                    actor_mode=actor_mode,
                )
                self.session.commit()
            except ValueError as exc:
                self.session.rollback()
                form.review_comment.errors = list(form.review_comment.errors) + [
                    str(exc)
                ]
            except Exception:
                self.session.rollback()
                logging.exception("Failed to transition dataset lifecycle.")
                flash("Failed to update the dataset lifecycle.", "error")
            else:
                flash(
                    f"Updated dataset {dataset.dataset_id} to "
                    f"{form.target_status.data}.",
                    "success",
                )
                return redirect(self.get_url(".review_view", id=dataset.dataset_id))

        return self.render(
            "admin/dataset_review.html",
            dataset=dataset,
            lifecycle=lifecycle,
            form=form,
            return_url=self.get_url(".index_view"),
        )

    @action("accept", "Accept", "Accept selected datasets?")
    def action_accept(self, ids):
        self._transition_selected(ids, REVIEW_STATUS_ACCEPTED)

    @action("resubmit", "Resubmit", "Return selected revisions to review?")
    def action_resubmit(self, ids):
        self._transition_selected(ids, REVIEW_STATUS_SUBMITTED)


admin = Admin(name="Dataset review")
admin.add_view(DatasetReviewAdmin(Dataset, db_session, category="Catalogue"))
