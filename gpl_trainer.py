from rgpl.query_models import QueryAugmentMod
from rgpl.utils import load_dataset, BEIR_DATASETS
from rgpl.query_models import QueryAugmentMod
from rgpl.lightning import GPLDistill
from pytorch_lightning.loggers import TensorBoardLogger
import pytorch_lightning as pl
from pytorch_lightning import seed_everything
import torch, gc
from typing import List
import hydra
from omegaconf import DictConfig
from pytorch_lightning.callbacks import ModelCheckpoint


def dataset(dataset_name: BEIR_DATASETS,
         output_folder: str):
    return load_dataset(dataset_name=dataset_name, output_folder=output_folder)

def train(path : str,
             cross_encoders: List[str],
             bi_retriver: str,
             t_total: int,
             eval_every: int,
             remine_hard_negatives_every:int,
             batch_size: int,
             warmup_steps: int,
             amp_training : bool,
             evaluate_baseline: bool,
             max_seq_length: int,
             seed: int,
             name: str,
             q_per_passage: int, 
             augmented_mod: QueryAugmentMod,
             prefix: str,
             reducer: str,
             bm25_reweight: bool,
             corpus_name: str,
             bm25_weight: int,
             load_test : bool,
             ):
    
    # assert remine_hard_negatives_every % 1000 == 0, "Remine Hard Negatives Every needs to be divisible by 1000"
    
    logger = TensorBoardLogger("tb_logs_extension", name=f"{corpus_name}_{name}")
    
    
    # We save the model every time we evalaute the performance
    # Also we save the last one.
    checkpoint_callback = ModelCheckpoint(dirpath=f'./saved_models/gpl_improved/{corpus_name}_{name}',
                                          filename='{epoch}-{step:.2f}',
                                          verbose = True,
                                          every_n_train_steps = eval_every,
                                          save_top_k = -1,
                                          every_n_epochs = None,
                                          save_last = True)
    seed_everything(seed, workers = True)
    trainer = pl.Trainer(logger = logger, gpus = 1, max_epochs = -1, max_steps = t_total, 
                         deterministic = True,
                         limit_train_batches = 1000,
                         callbacks = [checkpoint_callback],
                         reload_dataloaders_every_n_epochs = remine_hard_negatives_every // 1000,
                         log_every_n_steps=10)
    print(f"Remining hard negatives every : {remine_hard_negatives_every // 1000} epochs")
    distill = GPLDistill(cross_encoder= cross_encoders,
                         bi_retriver = bi_retriver, 
                         path = path,
                         amp_training = amp_training, 
                         batch_size = batch_size, 
                         evaluate_baseline=evaluate_baseline,
                         eval_every=eval_every,
                         remine_hard_negatives_every=remine_hard_negatives_every,
                         warmup_steps=warmup_steps,
                         max_seq_length=max_seq_length,
                         query_per_passage=q_per_passage,
                         augmented_mod=augmented_mod,
                         save_name = name,
                         prefix = prefix,
                         reducer = reducer,
                         bm25_reweight= bm25_reweight,
                         corpus_name = corpus_name,
                         bm25_weight= bm25_weight,
                         load_test=load_test
                         )


    trainer.fit(model=distill)
    
    
    
@hydra.main(version_base = None, config_path=".", config_name="config")
def main(cfg: DictConfig) -> None:
    if cfg.data.given_path == "":
        path = dataset(dataset_name=BEIR_DATASETS(cfg.data.dataset_name), output_folder=cfg.data.output_folder)
    else:
        path = cfg.data.given_path
    train(path = path, 
        cross_encoders = cfg.trainer.cross_encoders, 
        bi_retriver = cfg.trainer.bi_retriver, 
        t_total = cfg.trainer.t_total, 
        eval_every = cfg.trainer.eval_every,
        remine_hard_negatives_every=cfg.trainer.remine_hard_negatives_every, 
        batch_size = cfg.trainer.batch_size, 
        warmup_steps = cfg.trainer.warmup_steps, 
        amp_training = cfg.trainer.amp_training,
        evaluate_baseline = cfg.trainer.evaluate_baseline, 
        max_seq_length = cfg.trainer.max_seq_length, 
        seed = cfg.trainer.seed,
        name = cfg.trainer.name,
        q_per_passage= 3,
        augmented_mod= QueryAugmentMod(cfg.query_writer.augmented),
        prefix = cfg.data.prefix,
        reducer = cfg.trainer.reducer,
        bm25_reweight = cfg.beir_evaluator.bm25_reweight,
        corpus_name = cfg.beir_evaluator.corpus_name,
        bm25_weight = cfg.beir_evaluator.bm25_weight,
        load_test = cfg.trainer.load_test
        )
    
if __name__ == "__main__":
    gc.collect()
    torch.cuda.empty_cache()
    main()
    gc.collect()
    torch.cuda.empty_cache()
