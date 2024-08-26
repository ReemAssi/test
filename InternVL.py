#!/usr/bin/env python
# coding: utf-8

# # OpenGVLab/InternVL-Chat-V1-5

# In[1]:


get_ipython().system('nvidia-smi')


# In[2]:


import numpy as np
import torch
import torchvision.transforms as T
from decord import VideoReader, cpu
from PIL import Image
from torchvision.transforms.functional import InterpolationMode
from transformers import AutoModel, AutoTokenizer
import decord
import cv2
import matplotlib.pyplot as plt
import time 

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def build_transform(input_size):
    MEAN, STD = IMAGENET_MEAN, IMAGENET_STD
    transform = T.Compose([
        T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
        T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
        T.ToTensor(),
        T.Normalize(mean=MEAN, std=STD)
    ])
    return transform


def find_closest_aspect_ratio(aspect_ratio, target_ratios, width, height, image_size):
    best_ratio_diff = float('inf')
    best_ratio = (1, 1)
    area = width * height
    for ratio in target_ratios:
        target_aspect_ratio = ratio[0] / ratio[1]
        ratio_diff = abs(aspect_ratio - target_aspect_ratio)
        if ratio_diff < best_ratio_diff:
            best_ratio_diff = ratio_diff
            best_ratio = ratio
        elif ratio_diff == best_ratio_diff:
            if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                best_ratio = ratio
    return best_ratio


def dynamic_preprocess(image, min_num=1, max_num=6, image_size=448, use_thumbnail=False):
    orig_width, orig_height = image.size
    aspect_ratio = orig_width / orig_height

    # calculate the existing image aspect ratio
    target_ratios = set(
        (i, j) for n in range(min_num, max_num + 1) for i in range(1, n + 1) for j in range(1, n + 1) if
        i * j <= max_num and i * j >= min_num)
    target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])

    # find the closest aspect ratio to the target
    target_aspect_ratio = find_closest_aspect_ratio(
        aspect_ratio, target_ratios, orig_width, orig_height, image_size)

    # calculate the target width and height
    target_width = image_size * target_aspect_ratio[0]
    target_height = image_size * target_aspect_ratio[1]
    blocks = target_aspect_ratio[0] * target_aspect_ratio[1]

    # resize the image
    resized_img = image.resize((target_width, target_height))
    processed_images = []
    for i in range(blocks):
        box = (
            (i % (target_width // image_size)) * image_size,
            (i // (target_width // image_size)) * image_size,
            ((i % (target_width // image_size)) + 1) * image_size,
            ((i // (target_width // image_size)) + 1) * image_size
        )
        # split the image
        split_img = resized_img.crop(box)
        processed_images.append(split_img)
    assert len(processed_images) == blocks
    if use_thumbnail and len(processed_images) != 1:
        thumbnail_img = image.resize((image_size, image_size))
        processed_images.append(thumbnail_img)
    return processed_images


def load_image(image_file, input_size=448, max_num=6):
    image = Image.open(image_file).convert('RGB')
    transform = build_transform(input_size=input_size)
    images = dynamic_preprocess(image, image_size=input_size, use_thumbnail=True, max_num=max_num)
    pixel_values = [transform(image) for image in images]
    pixel_values = torch.stack(pixel_values)
    return pixel_values


path = 'OpenGVLab/InternVL-Chat-V1-5'
# # If you have an 80G A100 GPU, you can put the entire model on a single GPU.
# model = AutoModel.from_pretrained(
#     path,
#     torch_dtype=torch.bfloat16,
#     low_cpu_mem_usage=False,
#     trust_remote_code=True).eval().cuda()
# Otherwise, you need to set device_map='auto' to use multiple GPUs for inference.
import os
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
model = AutoModel.from_pretrained(
    path,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
    trust_remote_code=True,
    device_map='auto').eval()


# In[3]:


tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
# set the max number of tiles in `max_num`

generation_config = dict(
    num_beams=1,
    max_new_tokens=1024,
    do_sample=False,
)


# In[5]:


question = 'هل تفهم اللغة العربية'
response, history = model.chat(tokenizer, None, question, generation_config, history=None, return_history=True)
print(f'User: {question}')
print(f'Assistant: {response}')


# In[10]:


import cv2
import matplotlib.pyplot as plt

# img = cv2.imread("ara.png")
# plt.imshow(img)


pixel_values = load_image('ar.png', max_num=6).to(torch.bfloat16).cuda()

# single-image single-round conversation (单图单轮对话)
question = '<image>\n can you understand what is written in arabic?'
response = model.chat(tokenizer, pixel_values, question, generation_config)
print(f'User: {question}')
print(f'Assistant: {response}')


# In[6]:


import cv2
import matplotlib.pyplot as plt
start_time = time.time()

img = cv2.imread("img4.jpeg")
plt.imshow(img)


pixel_values = load_image('img4.jpeg', max_num=6).to(torch.bfloat16).cuda()

# single-image single-round conversation (单图单轮对话)
question = '<image>\n what is wrtitten in this paper?'
response = model.chat(tokenizer, pixel_values, question, generation_config)
print(f'User: {question}')
print(f'Assistant: {response}')

end_time = time.time()
execution_time = end_time - start_time

print(f"Execution time: {execution_time} seconds")


# In[5]:


start_time = time.time()

# img = cv2.imread("img2.jpeg")
# plt.imshow(img)


pixel_values = load_image('img2.jpeg', max_num=6).to(torch.bfloat16).cuda()

# single-image single-round conversation (单图单轮对话)
question = '<image>\nAnalyze the given image in a detail manner, provide test name along with its result as json format'
response = model.chat(tokenizer, pixel_values, question, generation_config)
print(f'User: {question}')
print(f'Assistant: {response}')

end_time = time.time()
execution_time = end_time - start_time

print(f"Execution time: {execution_time} seconds")


# In[17]:


import cv2
import matplotlib.pyplot as plt

img = cv2.imread("img2.jpeg")
plt.imshow(img)


pixel_values = load_image('img2.jpeg', max_num=6).to(torch.bfloat16).cuda()

# single-image single-round conversation (单图单轮对话)
question = '<image>\nAnalyze the given image in a detail manner, provide test name along with its result as json format'
response = model.chat(tokenizer, pixel_values, question, generation_config)
print(f'User: {question}')
print(f'Assistant: {response}')


# In[7]:


start_time = time.time()

# img = cv2.imread("img2.jpeg")
# plt.imshow(img)


pixel_values = load_image('img2.jpeg', max_num=6).to(torch.bfloat16).cuda()

# single-image single-round conversation (单图单轮对话)
question = '<image>\nAnalyze the given image in a detail manner, provide test name along with its result as json format'
response = model.chat(tokenizer, pixel_values, question, generation_config)
print(f'User: {question}')
print(f'Assistant: {response}')

end_time = time.time()
execution_time = end_time - start_time

print(f"Execution time: {execution_time} seconds")


# In[21]:


import cv2
import matplotlib.pyplot as plt

img = cv2.imread("enhanced.jpg")
plt.imshow(img)


pixel_values = load_image('enhanced.jpg', max_num=6).to(torch.bfloat16).cuda()

# single-image single-round conversation (单图单轮对话)
question = '<image>\nAnalyze the given image in a detail manner, provide test name behind its result as json format'
response = model.chat(tokenizer, pixel_values, question, generation_config)
print(f'User: {question}')
print(f'Assistant: {response}')


# In[25]:


import cv2
import matplotlib.pyplot as plt

# img = cv2.imread("img5.png")
# plt.imshow(img)


pixel_values = load_image('img5.png', max_num=6).to(torch.bfloat16).cuda()

# single-image single-round conversation (单图单轮对话)
question = '<image>\nAnalyze the given image in a detail manner, provide test name behind its result as json format'
response = model.chat(tokenizer, pixel_values, question, generation_config)
print(f'User: {question}')
print(f'Assistant: {response}')


# In[26]:


import cv2
import matplotlib.pyplot as plt

img = cv2.imread("enhanced5.jpg")
plt.imshow(img)


pixel_values = load_image('enhanced5.jpg', max_num=6).to(torch.bfloat16).cuda()

# single-image single-round conversation (单图单轮对话)
question = '<image>\nAnalyze the given image in a detail manner, provide test name behind its result as json format'
response = model.chat(tokenizer, pixel_values, question, generation_config)
print(f'User: {question}')
print(f'Assistant: {response}')


# In[5]:


from pdf2image import convert_from_path
def load_images_from_pdf(pdf_path, dpi=300):
    images = convert_from_path(pdf_path, dpi=dpi)
    return images


# In[4]:


start_time = time.time()

pdf_path = "t3.pdf"  # Replace with your PDF file path
images = load_images_from_pdf(pdf_path)
for i, image in enumerate(images):
    print('page #',i+1)
    image_path = f"temp_image_{i}.png"
    image.save(image_path)
    pixel_values = load_image(image_path, max_num=6).to(torch.bfloat16).cuda()

    question = '<image>\n answer only with yes or no, is this a lab test image with test names and their result? '
    response = model.chat(tokenizer, pixel_values, question, generation_config)
    
#     print(f'User: {question}')
#     print(f'Assistant: {response}')
    
    if 'yes' in response.lower():
        question = '<image>\n Please provide all test names along with their results and indicate if each result is normal or not. Format the response as JSON.'
        response = model.chat(tokenizer, pixel_values, question, generation_config)
        print(f'Assistant: {response}')

    else: 
        print('Not a lab test')
        

    os.remove(image_path)
    
end_time = time.time()
execution_time = end_time - start_time

print(f"Execution time: {execution_time} seconds")  


# In[ ]:




