# coding=utf-8
# Copyright 2023 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import tempfile
import unittest

from transformers import PoNetConfig, is_torch_available
from transformers.models.auto import get_values
from transformers.testing_utils import require_torch, require_torch_gpu, slow, torch_device

from ...test_configuration_common import ConfigTester
from ...test_modeling_common import ModelTesterMixin, ids_tensor, random_attention_mask
from ...test_pipeline_mixin import PipelineTesterMixin


if is_torch_available():
    import torch

    from transformers import (
        MODEL_FOR_PRETRAINING_MAPPING,
        PoNetForPreTraining,
        PoNetForSequenceClassification,
        PoNetModel,
    )
    from transformers.models.ponet.modeling_ponet import PONET_PRETRAINED_MODEL_ARCHIVE_LIST


class PoNetModelTester:
    def __init__(
        self,
        parent,
        batch_size=13,
        seq_length=7,
        is_training=True,
        use_input_mask=True,
        use_token_type_ids=True,
        use_labels=True,
        vocab_size=99,
        hidden_size=32,
        num_hidden_layers=5,
        num_attention_heads=4,
        intermediate_size=37,
        hidden_act="gelu",
        hidden_dropout_prob=0.1,
        attention_probs_dropout_prob=0.1,
        max_position_embeddings=512,
        type_vocab_size=16,
        type_sequence_label_size=2,
        initializer_range=0.02,
        num_labels=3,
        num_choices=4,
        scope=None,
    ):
        self.parent = parent
        self.batch_size = batch_size
        self.seq_length = seq_length
        self.is_training = is_training
        self.use_input_mask = use_input_mask
        self.use_token_type_ids = use_token_type_ids
        self.use_labels = use_labels
        self.vocab_size = vocab_size
        self.hidden_size = hidden_size
        self.num_hidden_layers = num_hidden_layers
        self.num_attention_heads = num_attention_heads
        self.intermediate_size = intermediate_size
        self.hidden_act = hidden_act
        self.hidden_dropout_prob = hidden_dropout_prob
        self.attention_probs_dropout_prob = attention_probs_dropout_prob
        self.max_position_embeddings = max_position_embeddings
        self.type_vocab_size = type_vocab_size
        self.type_sequence_label_size = type_sequence_label_size
        self.initializer_range = initializer_range
        self.num_labels = num_labels
        self.num_choices = num_choices
        self.scope = scope

    def prepare_config_and_inputs(self):
        input_ids = ids_tensor([self.batch_size, self.seq_length], self.vocab_size)

        input_mask = None
        if self.use_input_mask:
            input_mask = random_attention_mask([self.batch_size, self.seq_length])

        token_type_ids = None
        if self.use_token_type_ids:
            token_type_ids = ids_tensor([self.batch_size, self.seq_length], self.type_vocab_size)

        sequence_labels = None
        token_labels = None
        choice_labels = None
        if self.use_labels:
            sequence_labels = ids_tensor([self.batch_size], self.type_sequence_label_size)
            token_labels = ids_tensor([self.batch_size, self.seq_length], self.num_labels)
            choice_labels = ids_tensor([self.batch_size], self.num_choices)

        config = self.get_config()

        return config, input_ids, token_type_ids, input_mask, sequence_labels, token_labels, choice_labels

    def get_config(self):
        """
        Returns a tiny configuration by default.
        """
        return PoNetConfig(
            vocab_size=self.vocab_size,
            hidden_size=self.hidden_size,
            num_hidden_layers=self.num_hidden_layers,
            num_attention_heads=self.num_attention_heads,
            intermediate_size=self.intermediate_size,
            hidden_act=self.hidden_act,
            hidden_dropout_prob=self.hidden_dropout_prob,
            attention_probs_dropout_prob=self.attention_probs_dropout_prob,
            max_position_embeddings=self.max_position_embeddings,
            type_vocab_size=self.type_vocab_size,
            is_decoder=False,
            initializer_range=self.initializer_range,
        )

    def create_and_check_model(
        self, config, input_ids, token_type_ids, input_mask, sequence_labels, token_labels, choice_labels
    ):
        model = PoNetModel(config=config)
        model.to(torch_device)
        model.eval()
        result = model(input_ids, attention_mask=input_mask, token_type_ids=token_type_ids)
        result = model(input_ids, token_type_ids=token_type_ids)
        result = model(input_ids)
        self.parent.assertEqual(result.last_hidden_state.shape, (self.batch_size, self.seq_length, self.hidden_size))
        self.parent.assertEqual(result.pooler_output.shape, (self.batch_size, self.hidden_size))

    def create_and_check_for_pretraining(
        self, config, input_ids, token_type_ids, input_mask, sequence_labels, token_labels, choice_labels
    ):
        model = PoNetForPreTraining(config=config)
        model.to(torch_device)
        model.eval()
        result = model(
            input_ids,
            attention_mask=input_mask,
            token_type_ids=token_type_ids,
            labels=token_labels,
            sentence_structural_label=sequence_labels,
        )
        self.parent.assertEqual(result.prediction_logits.shape, (self.batch_size, self.seq_length, self.vocab_size))
        self.parent.assertEqual(result.seq_relationship_logits.shape, (self.batch_size, 3))

    def create_and_check_for_sequence_classification(
        self, config, input_ids, token_type_ids, input_mask, sequence_labels, token_labels, choice_labels
    ):
        config.num_labels = self.num_labels
        model = PoNetForSequenceClassification(config)
        model.to(torch_device)
        model.eval()
        result = model(input_ids, attention_mask=input_mask, token_type_ids=token_type_ids, labels=sequence_labels)
        self.parent.assertEqual(result.logits.shape, (self.batch_size, self.num_labels))

    def prepare_config_and_inputs_for_common(self):
        config_and_inputs = self.prepare_config_and_inputs()
        (
            config,
            input_ids,
            token_type_ids,
            input_mask,
            sequence_labels,
            token_labels,
            choice_labels,
        ) = config_and_inputs
        inputs_dict = {"input_ids": input_ids, "token_type_ids": token_type_ids, "attention_mask": input_mask}
        return config, inputs_dict


@require_torch
class PoNetModelTest(ModelTesterMixin, PipelineTesterMixin, unittest.TestCase):
    all_model_classes = (
        (
            PoNetModel,
            PoNetForPreTraining,
            PoNetForSequenceClassification,
        )
        if is_torch_available()
        else ()
    )
    pipeline_model_mapping = (
        {
            "feature-extraction": PoNetModel,
            "text-classification": PoNetForSequenceClassification,
            "zero-shot": PoNetForSequenceClassification,
        }
        if is_torch_available()
        else {}
    )
    fx_compatible = False
    test_attention_outputs = False
    test_head_masking = False
    test_pruning = False
    test_inputs_embeds = False
    # test_resize_embeddings = False
    # test_torchscript = False

    # special case for ForPreTraining model
    def _prepare_for_class(self, inputs_dict, model_class, return_labels=False):
        inputs_dict = super()._prepare_for_class(inputs_dict, model_class, return_labels=return_labels)

        if return_labels:
            if model_class in get_values(MODEL_FOR_PRETRAINING_MAPPING):
                inputs_dict["labels"] = torch.zeros(
                    (self.model_tester.batch_size, self.model_tester.seq_length), dtype=torch.long, device=torch_device
                )
                inputs_dict["sentence_structural_label"] = torch.zeros(
                    self.model_tester.batch_size, dtype=torch.long, device=torch_device
                )
        return inputs_dict

    def setUp(self):
        self.model_tester = PoNetModelTester(self)
        self.config_tester = ConfigTester(self, config_class=PoNetConfig, hidden_size=37)

    def test_config(self):
        self.config_tester.run_common_tests()

    def test_model(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        self.model_tester.create_and_check_model(*config_and_inputs)

    def test_for_pretraining(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        self.model_tester.create_and_check_for_pretraining(*config_and_inputs)

    def test_for_sequence_classification(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        self.model_tester.create_and_check_for_sequence_classification(*config_and_inputs)

    @slow
    def test_model_from_pretrained(self):
        for model_name in PONET_PRETRAINED_MODEL_ARCHIVE_LIST[:1]:
            model = PoNetModel.from_pretrained(model_name)
            self.assertIsNotNone(model)

    @slow
    @require_torch_gpu
    def test_torchscript_device_change(self):
        config, inputs_dict = self.model_tester.prepare_config_and_inputs_for_common()
        for model_class in self.all_model_classes:
            config.torchscript = True
            model = model_class(config=config)

            inputs_dict = self._prepare_for_class(inputs_dict, model_class)
            traced_model = torch.jit.trace(
                model, (inputs_dict["input_ids"].to("cpu"), inputs_dict["attention_mask"].to("cpu"))
            )

            with tempfile.TemporaryDirectory() as tmp:
                torch.jit.save(traced_model, os.path.join(tmp, "ponet.pt"))
                loaded = torch.jit.load(os.path.join(tmp, "ponet.pt"), map_location=torch_device)
                loaded(inputs_dict["input_ids"].to(torch_device), inputs_dict["attention_mask"].to(torch_device))


@require_torch
class PoNetModelIntegrationTest(unittest.TestCase):
    @slow
    def test_inference_no_head_absolute_embedding(self):
        model = PoNetModel.from_pretrained("chtan/ponet-base-uncased")
        input_ids = torch.tensor([[0, 345, 232, 328, 740, 140, 1695, 69, 6078, 1588, 2]])
        attention_mask = torch.tensor([[0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]])
        with torch.no_grad():
            output = model(input_ids, attention_mask=attention_mask)[0]
        expected_shape = torch.Size((1, 11, 768))
        self.assertEqual(output.shape, expected_shape)
        expected_slice = torch.tensor([[[0.4249, 0.1008, 0.7531], [0.3771, 0.1188, 0.7467], [0.4152, 0.1098, 0.7108]]])

        self.assertTrue(torch.allclose(output[:, 1:4, 1:4], expected_slice, atol=1e-4))