import os
import time

import pandas as pd
from flair.data import Sentence
from flair.datasets import ClassificationCorpus
from flair.embeddings import WordEmbeddings, DocumentPoolEmbeddings
from flair.models import TextClassifier
from flair.trainers import ModelTrainer
from sklearn.model_selection import train_test_split


class SentimentClassifier:
    def __init__(self,
                 file_name: str = 'sentiment_complaints.csv',
                 data_path: str = './data/raw_data',
                 output_data_path: str = './data/Sentiment Classifier/corpus',
                 model_path: str = './data/Sentiment Classifier/model',
                 complaint_severity: dict = None):
        """

        :param file_name:
        :param data_path:
        :param output_data_path:
        :param model_path:
        :param complaint_severity:
        """
        self.data = pd.read_csv(os.path.join(data_path, file_name))

        if complaint_severity is not None:
            self.complaint_severity = complaint_severity
        else:
            self.complaint_severity = {
                0: 'Very Severe',
                1: 'Severe',
                2: 'Can Improve',
                3: 'Can Improve',
                4: 'Can Improve',
                5: 'Can Improve'
            }

        self.reverse_mapping = {v: idx for idx, v in enumerate(list(self.complaint_severity.values()))}

        self.output_data_path = output_data_path
        self.model_path = model_path
        self.data_path = data_path

        if not os.path.exists(self.output_data_path):
            os.makedirs(self.output_data_path)

        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
            self.sentiment_model = None
        else:
            self.sentiment_model = TextClassifier.load(os.path.join(self.model_path, 'final-model.pt'))

    def _clean_location(self, x):
        """

        :param x:
        :return:
        """
        if ", " in x:
            return x.split(", ")[-1]
        return x

    def restructure_data(self):
        """

        :return:
        """
        self.data['posted_on'] = pd.to_datetime(self.data.posted_on)
        self.data['year'] = self.data['posted_on'].dt.year
        self.data[['Author', 'Location']] = self.data.author.apply(lambda x: pd.Series(str(x).split(" of ")))
        self.data['State'] = self.data['Location'].apply(self._clean_location)

        self.data = self.data.drop(['author', 'Location', 'posted_on'], axis=1)
        self.data['rating'] = self.data['rating'].map(self.complaint_severity)

    def _clean_text(self, x):
        """

        :param x:
        :return:
        """
        if not isinstance(x, str):
            return ""

        return x.encode('ascii', errors='ignore').decode()

    def clean_text(self):
        """

        :return:
        """
        print("Cleaning text")
        start_time = time.time()
        self.data['text'] = self.data['text'].apply(lambda x: self._clean_text(x))
        print(f"Done cleaning ({time.time() - start_time})")
        print('*' * 89)
        print()

    def make_corpus(self):
        """

        :return:
        """
        data = self.data[['rating', 'text']]
        data['rating'] = data['rating'].map(self.reverse_mapping)

        train, test = train_test_split(data, test_size=0.2, stratify=data['rating'])
        dev, test = train_test_split(test, test_size=0.5, stratify=test['rating'])

        with open(os.path.join(self.output_data_path, 'train.txt'), 'w') as f:
            for rating, text in zip(train['rating'], train['text']):
                f.write(f"__label__{rating} {text}\n")

        with open(os.path.join(self.output_data_path, 'test.txt'), 'w') as f:
            for rating, text in zip(test['rating'], test['text']):
                f.write(f"__label__{rating} {text}\n")

        with open(os.path.join(self.output_data_path, 'dev.txt'), 'w') as f:
            for rating, text in zip(dev['rating'], dev['text']):
                f.write(f"__label__{rating} {text}\n")

    def train(self,
              learning_rate: float = 0.1,
              mini_batch_size: int = 16,
              anneal_factor: float = 0.5,
              patience: int = 5,
              max_epochs: int = 10):
        """

        :return:
        """
        self.make_corpus()
        corpus = ClassificationCorpus(self.output_data_path,
                                      train_file='train.txt',
                                      dev_file='dev.txt',
                                      test_file='test.txt')

        label_dictionary = corpus.make_label_dictionary()

        embeddings = [WordEmbeddings('glove')]
        document_pool = DocumentPoolEmbeddings(embeddings)
        classifier = TextClassifier(document_pool, label_dictionary=label_dictionary)
        trainer = ModelTrainer(classifier, corpus)
        trainer.train(self.model_path,
                      learning_rate=learning_rate,
                      mini_batch_size=mini_batch_size,
                      anneal_factor=anneal_factor,
                      patience=patience,
                      max_epochs=max_epochs,
                      )

    def predict(self,
                x: str = 'test string'):
        """

        :param x:
        :return:
        """
        sentence = Sentence(x)
        self.sentiment_model.predict(sentence)
        print(sentence.labels)

    def eda(self):
        """
        Juhi -> Add the EDA plots in here
        :return:
        """
        pass

    def run(self):
        """

        :return:
        """
        self.restructure_data()
        self.clean_text()
        self.train()