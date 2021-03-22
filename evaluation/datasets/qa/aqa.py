# Copyright (c) Facebook, Inc. and its affiliates.

import json
import os
import sys
import tempfile

from datasets.common import logger

from .base import QaBase


class AqaBase(QaBase):
    def __init__(self, task, name, local_path, round_id=0):
        self.local_path = local_path
        super().__init__(task=task, name=name, round_id=round_id)

    def load(self):
        try:
            with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
                for line in open(self.local_path).readlines():
                    jl = json.loads(line)
                    tmp_jl = {
                        "uid": jl["id"],
                        "context": jl["context"],
                        "question": jl["question"],
                        "answer": jl["answers"][0]["text"],
                    }
                    tmp.write(json.dumps(tmp_jl) + "\n")
                tmp.close()
                response = self.s3_client.upload_file(
                    tmp.name, self.s3_bucket, self._get_data_s3_path()
                )
                os.remove(tmp.name)
                if response:
                    logger.info(response)
        except Exception as ex:
            logger.exception(f"Failed to load {self.name} to S3 due to {ex}.")
            return False
        else:
            return True

    def label_field_converter(self, example):
        return {
            "id": example["uid"],
            "answer": example["answer"],
            "tags": example.get("tags", []),
        }


class AqaRound1Test(AqaBase):
    def __init__(self):
        rootpath = os.path.dirname(sys.path[0])
        local_path = os.path.join(rootpath, "data", "aqa/aqa_v1.0/round1/test.jsonl")
        super().__init__(
            task="qa", name="aqa-r1-test", local_path=local_path, round_id=1
        )