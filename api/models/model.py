# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import enum
import sqlalchemy as db

from common import helpers as util
from models.user import User

from .base import Base, BaseModel


class DeploymentStatusEnum(enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    deployed = "deployed"
    created = "created"
    failed = "failed"
    unknown = "unknown"
    takendown = "takendown"
    predictions_upload = "predictions_upload"


class EvaluationStatusEnum(enum.Enum):
    evaluating = "evaluating"
    completed = "completed"
    pre_evaluation = "pre_evaluation"
    failed = "failed"


class Model(Base):
    __tablename__ = "models"
    __table_args__ = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_general_ci"}

    id = db.Column(db.Integer, primary_key=True)
    tid = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    task = db.orm.relationship("Task", foreign_keys="Model.tid")
    uid = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.orm.relationship("User", foreign_keys="Model.uid")

    name = db.Column(db.String(length=255), nullable=False)
    shortname = db.Column(db.String(length=255), nullable=False)

    desc = db.Column(db.String(length=255))
    longdesc = db.Column(db.Text)
    papers = db.Column(db.Text)

    # Model cards
    params = db.Column(db.BigInteger)
    languages = db.Column(db.Text)
    license = db.Column(db.Text)
    upload_datetime = db.Column(db.DateTime)
    model_card = db.Column(db.Text)
    source_url = db.Column(db.Text)

    is_published = db.Column(db.BOOLEAN, default=False)
    is_anonymous = db.Column(db.BOOLEAN, default=False)

    # deployment
    endpoint_name = db.Column(db.Text)
    deployment_status = db.Column(
        db.Enum(DeploymentStatusEnum), default=DeploymentStatusEnum.unknown
    )
    evaluation_status = db.Column(
        db.Enum(EvaluationStatusEnum), default=EvaluationStatusEnum.pre_evaluation
    )

    secret = db.Column(db.Text)

    def __repr__(self):
        return f"<Model {self.id}>"

    def to_dict(self, safe=True):
        d = {}
        for column in self.__table__.columns:
            if safe and column.name in ["secret", "user"]:
                continue
            d[column.name] = getattr(self, column.name)
        d["task"] = self.task.to_dict()
        return d


class ModelModel(BaseModel):
    def __init__(self):
        super().__init__(Model)

    def create(self, task_id, user_id, **kwargs):
        m = Model(tid=task_id, uid=user_id, **kwargs)
        self.dbs.add(m)
        self.dbs.flush()
        self.dbs.commit()
        return m

    def delete(self, model):
        self.dbs.delete(model)
        self.dbs.commit()
        return True

    def update(self, id, **kwargs):
        u = self.dbs.query(Model).filter(Model.id == id)
        u.update(kwargs)
        self.dbs.commit()

    def getUnpublishedModelByMid(self, id):
        # Model owner to fetch by id
        return self.dbs.query(Model).filter(Model.id == id).one()

    def getPublishedModel(self, id):
        return (
            self.dbs.query(Model)
            .filter(Model.id == id)
            .filter(Model.is_published == True)  # noqa
            .filter(Model.is_anonymous == False)  # noqa
            .one()
        )

    def getByTid(self, tid):
        return self.dbs.query(Model).filter(Model.tid == tid).all()

    def getUserModelsByUid(self, uid, is_current_user=False, n=5, offset=0):
        query_res = self.dbs.query(Model).filter(Model.uid == uid)
        if not is_current_user:
            query_res = query_res.filter(
                db.and_(Model.is_published == True, Model.is_anonymous == False)
            )  # noqa
        return query_res.limit(n).offset(offset * n), util.get_query_count(query_res)

    def getUserModelsByUidAndMid(self, uid, mid, is_current_user=False):
        query_res = (
            self.dbs.query(Model).filter(Model.uid == uid).filter(Model.id == mid)
        )
        if not is_current_user:
            query_res = query_res.filter(
                db.and_(Model.is_published == True, Model.is_anonymous == False)
            )  # noqa
        return query_res.one()

    def getModelUserByMid(self, id):
        return (
            self.dbs.query(Model, User)
            .join(User, User.id == Model.uid)
            .filter(Model.id == id)
            .one()
        )

    def getByDeploymentStatus(self, deployment_status):
        return (
            self.dbs.query(Model)
            .filter(Model.deployment_status == deployment_status)
            .all()
        )

    def getCountByUidTidAndHrDiff(self, uid, tid=-1, hr_diff=24):
        """
        Returns submissions of all time if hr_diff < 0
        Returns submissions of all tasks if tid == 0
        """
        base_query = self.dbs.query(db.func.count(Model.id)).filter(Model.uid == uid)
        if hr_diff >= 0:
            base_query = base_query.filter(
                db.func.timediff(db.func.now(), Model.upload_datetime)
                < db.func.time(f"{hr_diff:02}:00:00")
            )
        if tid != -1:
            base_query = base_query.filter(Model.tid == tid)
        return base_query.scalar()
