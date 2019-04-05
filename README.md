# transfer-nlp

This library is a playground NLP library, built on top of Pytorch. The goal is to gradually build a design that enable researchers and engineers to quickly implement new ideas, train NLP models and serve them in production.

You can have an overview of the high-level API on this [Colab Notebook](https://colab.research.google.com/drive/1DtC31eUejz1T0DsaEfHq_DOxEfanmrG1#scrollTo=Xzu3HPdGrnza), which shows how to use the framework on several examples.

The ideal use of this library is to provide a minimal implementation of a dataset loader, a vectorizer and a model. Then, given a config file with the experiment parameters, `runner.py` takes care of the training pipeline.


Before starting using this repository:

- create a virtual environment: `mkvirtualenv YourEnvName`
- clone the repository: `git clone https://github.com/feedly/transfer-nlp.git`
- Install requirements: `pip install -r requirements.txt`

Structure of the library:

`loaders`
- `transfer-nlp/loaders/vocabulary.py`: contains classes for vocabularies
- `transfer-nlp/loaders/vectorizers.py`: classes for vectorizers
- `transfer-nlp/loaders/loaders.py`: classes for dataset loaders

`transfer-nlp/models/`: contains implementations of NLP models

`transfer-nlp/embeddings`: contains utility functions for embeddings management

`transfer-nlp/experiments`: each experiment is defined as a json config file, defining the whole experiment

`transfer-nlp/runners`: contains the full training pipeline, given a config file experiment

 TODO:
 - Unit-test everything
 - Smooth the runner pipeline to enable multi-task training (without constraining the way we do multi-task, whether linear, hierarchical or else...)
 - Include examples using state of the art pre-trained models
 - Enable slack integration for model crashing / completion
 - Enable embeddings visualisation (see this project https://projector.tensorflow.org/)
 - Enable pre-trained models finetuning



This library builds on the book <cite>["Natural Language Processing with PyTorch"](https://www.amazon.com/dp/1491978236/)<cite> by Delip Rao and Brian McMahan for the initial experiments.
