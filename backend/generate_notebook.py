import json
import os

NOTEBOOK_PATH = "evaluation_experiment.ipynb"

cells = []

def add_markdown(text):
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in text.split("\n")]
    })

def add_code(text):
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in text.split("\n")]
    })

add_markdown("# BERT vs LSTM: Faculty Recommendation Engine Evaluation\nThis notebook evaluates the performance of the BERT-based `sentence-transformers` model against a simple LSTM baseline using ROC curves.")

add_code("""
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense, GlobalAveragePooling1D
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from sentence_transformers import SentenceTransformer
from sklearn.metrics import roc_curve, auc
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
import re

print("Libraries loaded successfully.")
""")

add_markdown("### 1. Generate Golden Dataset\nWe will extract specializations from `faculty_data.csv` to create a list of search queries, and assign labels (1 for relevant, 0 for irrelevant).")

add_code("""
# Load Faculty Data
df = pd.read_csv("faculty_data.csv")

# Clean Specialisation column
df['Specialisation'] = df['Specialisation'].fillna('General')

def clean_text(text):
    return re.sub(r'[^a-zA-Z0-9 ]', '', str(text).lower())

df['clean_spec'] = df['Specialisation'].apply(clean_text)

# Generate a pool of unique queries (specializations)
all_specs = " ".join(df['clean_spec'].tolist()).split()
# Filter common stop words roughly and get top keywords
stop_words = {'the', 'and', 'of', 'in', 'for', 'based', 'with', 'on'}
keywords = list(set([w for w in all_specs if w not in stop_words and len(w) > 4]))[:50] # using 50 keywords as queries

queries = []
faculty_docs = []
labels = []

# Create dataset
for faculty_idx, row in df.iterrows():
    combined_bio = f"{row['Specialisation']} {row['Designation']} {row['Name']}"
    clean_bio = clean_text(combined_bio)
    
    for query in keywords:
        queries.append(query)
        faculty_docs.append(combined_bio)
        
        # If the generated query keyword is in their specialization, label = 1, else 0
        if query in clean_bio:
            labels.append(1)
        else:
            labels.append(0)

df_dataset = pd.DataFrame({'query': queries, 'document': faculty_docs, 'label': labels})
print(f"Generated {len(df_dataset)} Query-Document pairs. Relevant: {sum(labels)}, Irrelevant: {len(labels) - sum(labels)}")
""")

add_markdown("### 2. LSTM Implementation\nWe will build a simple Siamese-style or concatenated embedding LSTM to classify whether the query matches the document. Because we generated this data, we'll quickly train it on a split so it learns *something*.")

add_code("""
# Tokenization for LSTM
max_vocab = 5000
max_len_query = 5
max_len_doc = 50

tokenizer = Tokenizer(num_words=max_vocab, oov_token="<OOV>")
tokenizer.fit_on_texts(df_dataset['query'].tolist() + df_dataset['document'].tolist())

query_seq = tokenizer.texts_to_sequences(df_dataset['query'].tolist())
doc_seq = tokenizer.texts_to_sequences(df_dataset['document'].tolist())

query_pad = pad_sequences(query_seq, maxlen=max_len_query)
doc_pad = pad_sequences(doc_seq, maxlen=max_len_doc)

y = np.array(df_dataset['label'])

# Train-test split (We only evaluate on test set to be fair)
q_train, q_test, d_train, d_test, y_train, y_test = train_test_split(
    query_pad, doc_pad, y, test_size=0.3, random_state=42
)

# Build LSTM model
# We concatenate query and document padded sequences to feed into one LSTM
X_train = np.concatenate([q_train, d_train], axis=1)
X_test = np.concatenate([q_test, d_test], axis=1)
total_max_len = max_len_query + max_len_doc

lstm_model = Sequential([
    Embedding(max_vocab, 32, input_length=total_max_len),
    LSTM(32, return_sequences=False),
    Dense(16, activation='relu'),
    Dense(1, activation='sigmoid') # outputs a probability between 0 and 1
])

lstm_model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
lstm_model.summary()

# Train the LSTM
history = lstm_model.fit(X_train, y_train, epochs=3, batch_size=32, validation_split=0.2, verbose=1)

# Get Predictions for LSTM on the Test set
lstm_pred_probs = lstm_model.predict(X_test).ravel()
""")

add_markdown("### 3. BERT (MiniLM) Implementation\nWe will use `sentence-transformers/all-MiniLM-L6-v2` matching the original backend implementation, compute cosine similarity, and use it as a probability score.")

add_code("""
bert_model = SentenceTransformer("all-MiniLM-L6-v2")

# We need the original text for the test set queries to feed to BERT
q_test_text = df_dataset['query'].iloc[y_test.argsort()[:len(y_test)]].tolist() # dummy alignment, we need actual test split text
# Let's cleanly grab the exact text corresponding to the test indices
_, _, _, _, _, _, _, test_indices = train_test_split(
    query_pad, doc_pad, y, np.arange(len(y)), test_size=0.3, random_state=42
)

q_test_text = df_dataset['query'].iloc[test_indices].tolist()
d_test_text = df_dataset['document'].iloc[test_indices].tolist()

print("Embedding Queries and Documents with BERT...")
# Embed
q_embeds = bert_model.encode(q_test_text, convert_to_tensor=True)
d_embeds = bert_model.encode(d_test_text, convert_to_tensor=True)

from torch.nn.functional import cosine_similarity
# Calculate cosine similarity
cos_sim = cosine_similarity(q_embeds, d_embeds).cpu().numpy()

# Transform bounds roughly to [0,1] for ROC if needed, or ROC can handle raw continuous scores
# Cosine similarities are between -1 and 1
bert_pred_probs = (cos_sim + 1) / 2
""")

add_markdown("### 4. Comprehensive Metric Comparison\nBeyond the ROC curve, we will compare Precision-Recall curves and inference speed.")

add_code("""
import time

# 4.1 Precision-Recall Curve
from sklearn.metrics import precision_recall_curve, average_precision_score

precision_lstm, recall_lstm, _ = precision_recall_curve(y_test, lstm_pred_probs)
ap_lstm = average_precision_score(y_test, lstm_pred_probs)

precision_bert, recall_bert, _ = precision_recall_curve(y_test, bert_pred_probs)
ap_bert = average_precision_score(y_test, bert_pred_probs)

plt.figure(figsize=(10, 7))
plt.step(recall_lstm, precision_lstm, color='blue', alpha=0.7, where='post', label=f'LSTM (AP = {ap_lstm:.3f})')
plt.step(recall_bert, precision_bert, color='red', alpha=0.7, where='post', label=f'BERT (AP = {ap_bert:.3f})')
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.ylim([0.0, 1.05])
plt.xlim([0.0, 1.0])
plt.title('Precision-Recall Curve Comparison')
plt.legend(loc="upper right")
plt.grid(True, alpha=0.3)
plt.show()

# 4.2 Inference Time Comparison
print("Measuring Inference Time...")
# Measure LSTM
start_time = time.time()
_ = lstm_model.predict(X_test, verbose=0)
lstm_time = time.time() - start_time

# Measure BERT
start_time = time.time()
_ = bert_model.encode(q_test_text, convert_to_tensor=True)
bert_time = time.time() - start_time

plt.figure(figsize=(8, 5))
models = ['LSTM', 'BERT (MiniLM)']
times = [lstm_time, bert_time]
plt.bar(models, times, color=['blue', 'red'])
plt.ylabel('Time (seconds)')
plt.title(f'Inference Time for {len(y_test)} Samples (Lower is better)')
for i, v in enumerate(times):
    plt.text(i, v + 0.01, f"{v:.4f}s", ha='center')
plt.show()
""")

add_markdown("### 5. Final ROC Curve\nSaving the final ROC curve for records.")

add_code("""
# Compute ROC metrics
fpr_lstm, tpr_lstm, _ = roc_curve(y_test, lstm_pred_probs)
roc_auc_lstm = auc(fpr_lstm, tpr_lstm)

fpr_bert, tpr_bert, _ = roc_curve(y_test, bert_pred_probs)
roc_auc_bert = auc(fpr_bert, tpr_bert)

plt.figure(figsize=(10, 7))
plt.plot(fpr_lstm, tpr_lstm, color='blue', lw=2, label=f'LSTM (AUC = {roc_auc_lstm:.3f})')
plt.plot(fpr_bert, tpr_bert, color='red', lw=2, label=f'BERT System (AUC = {roc_auc_bert:.3f})')
plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('Final ROC Curve Comparison')
plt.legend(loc="lower right")
plt.grid(True, alpha=0.3)
plt.show()
""")

notebook_json = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.9"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

with open(NOTEBOOK_PATH, 'w', encoding='utf-8') as f:
    json.dump(notebook_json, f, indent=2)

print(f"Created {NOTEBOOK_PATH} successfully!")
