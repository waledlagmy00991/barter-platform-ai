"""Low-memory inference for the same frozen multilingual MiniLM encoder.

Quantized ONNX changes floating point results. This is a test-hosting optimization,
not new training or a model-quality certification. No external inference calls.
"""
from pathlib import Path
import hashlib
import numpy as np

MODEL_REVISION = 'e8f8c211226b894fcb81acc59f3b34ba3efd5f42'
MODEL_REPO = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'

class OnnxEncoder:
    def __init__(self, root=None):
        import onnxruntime as ort
        import sentencepiece as spm
        root = Path(root or Path(__file__).parent/'encoder')
        model = root/'onnx/model_quint8_avx2.onnx'
        import json
        manifest = json.loads((root/'manifest.json').read_text())
        for name, digest in manifest['sha256'].items():
            h=hashlib.sha256()
            with (root/name).open('rb') as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):
                    h.update(chunk)
            if h.hexdigest() != digest:
                raise RuntimeError('Encoder artifact integrity check failed')
        self.tokenizer=spm.SentencePieceProcessor(model_file=str(root/'sentencepiece.bpe.model'))
        opts=ort.SessionOptions()
        opts.intra_op_num_threads=1
        opts.inter_op_num_threads=1
        opts.enable_cpu_mem_arena=False
        opts.enable_mem_pattern=False
        opts.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        opts.add_session_config_entry('session.disable_prepacking','1')
        self.session=ort.InferenceSession(str(model),sess_options=opts,providers=['CPUExecutionProvider'])
        self.inputs={x.name for x in self.session.get_inputs()}

    def get_embedding_dimension(self): return 384

    def encode(self, texts, normalize_embeddings=True, **kwargs):
        rows=[[0]+[i+1 if i else 3 for i in self.tokenizer.encode(text)][:126]+[2] for text in texts]
        width=max(map(len,rows))
        values={
            'input_ids':np.asarray([r+[1]*(width-len(r)) for r in rows],dtype=np.int64),
            'attention_mask':np.asarray([[1]*len(r)+[0]*(width-len(r)) for r in rows],dtype=np.int64),
            'token_type_ids':np.zeros((len(rows),width),dtype=np.int64),
        }
        hidden=self.session.run(None,{k:v for k,v in values.items() if k in self.inputs})[0]
        mask=values['attention_mask'][...,None].astype(np.float32)
        embeddings=(hidden*mask).sum(axis=1)/np.maximum(mask.sum(axis=1),1e-9)
        if normalize_embeddings:
            embeddings=embeddings/np.maximum(np.linalg.norm(embeddings,axis=1,keepdims=True),1e-12)
        return embeddings.astype(np.float32)
