import os
import sys
import torch
import numpy as np
import argparse
import random
import logging
from tqdm import tqdm

from model import TopicClssCNN
from dataset import Vocabulary


def eval_validation_set(filename, w2i, t2i, tokenizer, model, device):
    model.eval()
    data = []

    with open(filename, 'r') as f:
        for line in f:
            topic, text = line.lower().strip().split(" ||| ")
            sentence = tokenizer.tokenize(text)
            sentence = [w2i[w] for w in sentence]
            sentence += [w2i['[SEP]']]
            sentence = [w2i['[CLS]']] + sentence
            data.append((sentence, t2i[topic]))

    correct = 0
    total = 0
    confusion_matrix = np.zeros((len(t2i), len(t2i)), dtype=np.int32)
    with torch.no_grad():
        for sent, gt_topic in tqdm(data):
            sent = torch.tensor([sent]).type(torch.LongTensor).to(device)
            mask = torch.ones_like(sent).type(torch.FloatTensor).to(device)
            logits = model(sent, mask)
            _, pred_topic = torch.max(logits, 1)
            pred_topic = pred_topic.cpu().numpy()[0]

            confusion_matrix[pred_topic][gt_topic] += 1
            if pred_topic == gt_topic:
                correct += 1
            total += 1

    acc = correct/total
    return acc, confusion_matrix


def main(config):
    print("loading the best model...")
    vocabulary = Vocabulary()
    vocab_size = vocabulary.get_num_words()

    model = TopicClssCNN(
        vocab_size=vocab_size,  
        emb_size=config.emb_size,
        dropout=config.dropout,
        kernel_sizes=config.kernel_sizes,
        num_feat_maps=config.num_feat_maps,
        num_classes=config.num_classes)

    checkpoint = torch.load(config.checkpoint_dir)
    model.load_state_dict(checkpoint['state_dict'])

    if torch.cuda.is_available():
        device = torch.device("cuda:0")
    else:
        device = torch.device("cpu")
    
    model = model.to(device)

    filename = '/home/haochen/Projects/cnn-topic-classification/data/topicclass_valid.txt'
    
    acc, confusion_matrix = eval_validation_set(
        filename, vocabulary.w2i, vocabulary.t2i, model, device)

    print("\n {}".format(confusion_matrix))
    print("val acc: {0:.4f}".format(acc * 100))

    model_name = os.path.split(config.checkpoint_dir)[-1]
    txt_name = os.path.join(os.path.split(os.path.split(config.checkpoint_dir)[0])[
                            0], 'results', 'val_acc_{}.txt'.format(model_name))
    result_str = "val acc: {0:.4f}".format(acc * 100)
    with open(txt_name, 'a') as f:
        result_str += '\n'
        f.write(result_str)





if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CNN text classificer')

    # model
    parser.add_argument('--dropout', type=float, default=0.5, help='the probability for dropout [default: 0.3]')
    parser.add_argument('--emb-size', type=int, default=300, help='number of embedding dimension [default: 200]')
    parser.add_argument('--num-classes', type=int, default=16, help='number of tpoics [default: 16]')
    parser.add_argument('--num-feat-maps', type=int, default=100,help='number of feature maps output of cnn [default: 100]')
    parser.add_argument('--kernel-sizes', nargs='+', default=[3, 4, 5], help='kernel sizes [default: [3, 4, 5]]')

    # device
    parser.add_argument('--checkpoint_dir', type=str, help='pretrained checkpoint')
    config = parser.parse_args()
    
    main(config)
