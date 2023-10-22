[![PyPI version](https://badge.fury.io/py/pyautogen.svg)](https://badge.fury.io/py/pyautogen)
[![Build](https://github.com/microsoft/autogen/actions/workflows/python-package.yml/badge.svg)](https://github.com/microsoft/autogen/actions/workflows/python-package.yml)
![Python Version](https://img.shields.io/badge/3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-blue)
[![Downloads](https://static.pepy.tech/badge/pyautogen/week)](https://pepy.tech/project/pyautogen)
[![](https://img.shields.io/discord/1153072414184452236?logo=discord&style=flat)](https://discord.gg/pAbnFJrkgZ)

यह प्रोजेक्ट [FLAML](https://github.com/microsoft/FLAML) का स्पिनऑफ़ है।

# ऑटोजेन

:फायर: ऑटोजेन ने [FLAML](https://github.com/microsoft/FLAML) से एक नए प्रोजेक्ट में प्रवेश किया है।

## ऑटोजेन क्या है

ऑटोजेन एक ढांचा है जो कई एजेंटों का उपयोग करके एलएलएम अनुप्रयोगों के विकास को सक्षम बनाता है जो कार्यों को हल करने के लिए एक दूसरे के साथ बातचीत कर सकते हैं। ऑटोजेन एजेंट अनुकूलन योग्य, संवाद योग्य हैं और निर्बाध रूप से मानव भागीदारी की अनुमति देते हैं। वे विभिन्न तरीकों से काम कर सकते हैं जो एलएलएम, मानव इनपुट और उपकरणों के संयोजन को नियोजित करते हैं।

![ऑटोजेन अवलोकन](https://github.com/microsoft/autogen/blob/main/website/static/img/autogen_agentchat.png)

- ऑटोजेन न्यूनतम प्रयास के साथ **मल्टी-एजेंट वार्तालाप** के आधार पर अगली पीढ़ी के एलएलएम एप्लिकेशन बनाने में सक्षम बनाता है। यह जटिल एलएलएम वर्कफ़्लो के ऑर्केस्ट्रेशन, स्वचालन और अनुकूलन को सरल बनाता है। यह एलएलएम मॉडल के प्रदर्शन को अधिकतम करता है और उनकी कमजोरियों को दूर करता है।
- यह जटिल वर्कफ़्लो के लिए **विविध वार्तालाप पैटर्न** का समर्थन करता है। अनुकूलन योग्य और संवादी एजेंटों के साथ, डेवलपर्स वार्तालाप स्वायत्तता से संबंधित वार्तालाप पैटर्न की एक विस्तृत श्रृंखला बनाने के लिए ऑटोजेन का उपयोग कर सकते हैं,
एजेंटों की संख्या, और एजेंट वार्तालाप टोपोलॉजी।
- यह विभिन्न जटिलताओं के साथ कार्य प्रणालियों का एक संग्रह प्रदान करता है। ये प्रणालियाँ विभिन्न डोमेन और जटिलताओं से **अनुप्रयोगों की एक विस्तृत श्रृंखला** तक फैली हुई हैं। यह दर्शाता है कि ऑटोजेन कैसे विविध वार्तालाप पैटर्न का आसानी से समर्थन कर सकता है।
- AutoGen एक **उन्नत अनुमान एपीआई** के रूप में `openai.Completion` या `openai.ChatCompletion` का ड्रॉप-इन प्रतिस्थापन प्रदान करता है। यह आसान प्रदर्शन ट्यूनिंग, एपीआई एकीकरण और कैशिंग जैसी उपयोगिताओं और उन्नत उपयोग पैटर्न, जैसे त्रुटि प्रबंधन, मल्टी-कॉन्फिग अनुमान, संदर्भ प्रोग्रामिंग इत्यादि की अनुमति देता है।

ऑटोजेन माइक्रोसॉफ्ट, पेन स्टेट यूनिवर्सिटी और वाशिंगटन विश्वविद्यालय के सहयोगात्मक [शोध अध्ययन](https://microsoft.github.io/autogen/docs/Research) द्वारा संचालित है।

## जल्दी शुरू
खेलना शुरू करने का सबसे आसान तरीका है
1. जीथब कोडस्पेस का उपयोग करने के लिए नीचे क्लिक करें

 [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/microsoft/autogen?quickstart=1)

2. OAI_CONFIG_LIST_sample को /नोटबुक फ़ोल्डर में, नाम को OAI_CONFIG_LIST में कॉपी करें और सही कॉन्फ़िगरेशन सेट करें।
3. नोटबुक के साथ खेलना शुरू करें!



## स्थापना

ऑटोजेन को **पायथन संस्करण >=3.8** की आवश्यकता है। इसे पिप से स्थापित किया जा सकता है:
```bash
pip install pyautogen
```

अतिरिक्त विकल्पों के बिना न्यूनतम निर्भरताएँ स्थापित की जाती हैं। आप अपनी ज़रूरत की सुविधा के आधार पर अतिरिक्त विकल्प स्थापित कर सकते हैं।

[इंस्टालेशन](https://microsoft.github.io/autogen/docs/Installation) में और विकल्प ढूंढें।

[कोड निष्पादन](https://microsoft.github.io/autogen/docs/FAQ/#code-execution) के लिए, हम दृढ़ता से पायथन डॉकर पैकेज को स्थापित करने और डॉकर का उपयोग करने की सलाह देते हैं।

एलएलएम अनुमान कॉन्फ़िगरेशन के लिए, [FAQs](https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints) जांचें।

## मल्टी-एजेंट वार्तालाप ढांचा

ऑटोजेन एक सामान्य मल्टी-एजेंट वार्तालाप ढांचे के साथ अगली पीढ़ी के एलएलएम अनुप्रयोगों को सक्षम बनाता है। यह अनुकूलन योग्य और संवादी एजेंट प्रदान करता है जो एलएलएम, उपकरण और मनुष्यों को एकीकृत करता है।
कई सक्षम एजेंटों के बीच चैट को स्वचालित करके, कोई आसानी से उन्हें सामूहिक रूप से स्वायत्त रूप से या मानवीय प्रतिक्रिया के साथ कार्य करने के लिए मजबूर कर सकता है, जिसमें ऐसे कार्य भी शामिल हैं जिनमें कोड के माध्यम से टूल का उपयोग करने की आवश्यकता होती है।

इस उपयोग के मामले की विशेषताओं में शामिल हैं:

- **मल्टी-एजेंट वार्तालाप**: ऑटोजेन एजेंट कार्यों को हल करने के लिए एक-दूसरे के साथ संवाद कर सकते हैं। यह एकल एलएलएम की तुलना में अधिक जटिल और परिष्कृत अनुप्रयोगों की अनुमति देता है।
- **अनुकूलन**: ऑटोजेन एजेंटों को किसी एप्लिकेशन की विशिष्ट आवश्यकताओं को पूरा करने के लिए अनुकूलित किया जा सकता है। इसमें उपयोग के लिए एलएलएम चुनने की क्षमता, अनुमति देने के लिए मानव इनपुट के प्रकार और नियोजित करने के लिए उपकरण शामिल हैं।
- **मानवीय भागीदारी**: ऑटोजेन निर्बाध रूप से मानवीय भागीदारी की अनुमति देता है। इसका मतलब यह है कि मनुष्य आवश्यकतानुसार एजेंटों को इनपुट और फीडबैक प्रदान कर सकते हैं।

[उदाहरण](https://github.com/microsoft/autogen/blob/main/test/twoagent.py) के लिए,

```python
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
# Load LLM inference endpoints from an env variable or a file
# See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
# and OAI_CONFIG_LIST_sample
config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
# You can also set config_list directly as a list, for example, config_list = [{'model': 'gpt-4', 'api_key': '<your OpenAI API key here>'},]
assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
user_proxy = UserProxyAgent("user_proxy", code_execution_config={"work_dir": "coding"})
user_proxy.initiate_chat(assistant, message="Plot a chart of NVDA and TESLA stock price change YTD.")
# This initiates an automated chat between the two agents to solve the task
```

इस उदाहरण के साथ चलाया जा सकता है

```python
python test/twoagent.py
```

रेपो क्लोन होने के बाद.
नीचे दिया गया चित्र ऑटोजेन के साथ एक उदाहरण वार्तालाप प्रवाह दिखाता है।
![एजेंट चैट उदाहरण](https://github.com/microsoft/autogen/blob/main/website/static/img/chat_example.png)

कृपया इस सुविधा के लिए अधिक [कोड उदाहरण](https://microsoft.github.io/autogen/docs/Examples/AutoGen-AgentChat) ढूंढें।

## उन्नत एलएलएम अनुमान

ऑटोजेन चैटजीपीटी और जीपीटी-4 जैसे महंगे एलएलएम से उपयोगिता को अधिकतम करने में भी मदद करता है। यह ट्यूनिंग, कैशिंग, एरर हैंडलिंग और टेम्प्लेटिंग जैसी शक्तिशाली कार्यक्षमताओं को जोड़कर `openai.Completion` या `openai.ChatCompletion` का ड्रॉप-इन प्रतिस्थापन प्रदान करता है। उदाहरण के लिए, आप अपने स्वयं के ट्यूनिंग डेटा, सफलता मेट्रिक्स और बजट के साथ एलएलएम द्वारा पीढ़ियों को अनुकूलित कर सकते हैं।

```python
# perform tuning
config, analysis = autogen.Completion.tune(
data=tune_data,
metric="success",
mode="max",
eval_func=eval_func,
inference_budget=0.05,
optimization_budget=3,
num_samples=-1,
)
# perform inference for a test instance
response = autogen.Completion.create(context=test_instance, **config)
```

कृपया इस सुविधा के लिए अधिक [कोड उदाहरण](https://microsoft.github.io/autogen/docs/Examples/AutoGen-Inference) ढूंढें।

## दस्तावेज़ीकरण

आप ऑटोजेन के बारे में विस्तृत दस्तावेज़ [यहां] (https://microsoft.github.io/autogen/) पा सकते हैं।

इसके अलावा, आप पा सकते हैं:

- [शोध](https://microsoft.github.io/autogen/docs/Research), [ब्लॉगपोस्ट](https://microsoft.github.io/autogen/blog) ऑटोजेन के आसपास, और [पारदर्शिता FAQ](https://github.com/microsoft/autogen/blob/main/TRANSPARENCY_FAQS.md)

- [कलह](https://discord.gg/pAbnFJrkgZ)

- [योगदान मार्गदर्शिका](https://microsoft.github.io/autogen/docs/Contribute)

- [रोडमैप](https://github.com/orgs/microsoft/projects/989/views/3)

## उद्धरण

[ऑटोजेन](https://arxiv.org/abs/2308.08155)

```
@inproceedings{wu2023autogen,
title={AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation Framework},
author={Qingyun Wu and Gagan Bansal and Jieyu Zhang and Yiran Wu and Shaokun Zhang and Erkang Zhu and Beibin Li and Li Jiang and Xiaoyun Zhang and Chi Wang},
year={2023},
eprint={2308.08155},
archivePrefix={arXiv},
primaryClass={cs.AI}
}
```

[इकोऑप्टिजेन](https://arxiv.org/abs/2303.04673)

```
@inproceedings{wang2023EcoOptiGen,
title={Cost-Effective Hyperparameter Optimization for Large Language Model Generation Inference},
author={Chi Wang and Susan Xueqing Liu and Ahmed H. Awadallah},
year={2023},
booktitle={AutoML'23},
}
```

[मैथचैट](https://arxiv.org/abs/2306.01337)

```
@inproceedings{wu2023empirical,
title={An Empirical Study on Challenging Math Problem Solving with GPT-4},
author={Yiran Wu and Feiran Jia and Shaokun Zhang and Hangyu Li and Erkang Zhu and Yue Wang and Yin Tat Lee and Richard Peng and Qingyun Wu and Chi Wang},
year={2023},
booktitle={ArXiv preprint arXiv:2306.01337},
}
```

## योगदान देना

यह परियोजना योगदान और सुझावों का स्वागत करती है। अधिकांश योगदानों के लिए आपको इससे सहमत होना आवश्यक है
योगदानकर्ता लाइसेंस अनुबंध (सीएलए) यह घोषणा करता है कि आपके पास हमें अनुदान देने का अधिकार है और वास्तव में है
आपके योगदान का उपयोग करने का अधिकार। विवरण के लिए, <https://cla.opensource.microsoft.com> पर जाएँ।

यदि आप GitHub पर नए हैं तो [यहां](https://help.github.com/categories/collaborating-with-issues-and-pull-requests/) GitHub पर विकास में शामिल होने के लिए एक विस्तृत सहायता स्रोत है।

जब आप पुल अनुरोध सबमिट करते हैं, तो सीएलए बॉट स्वचालित रूप से निर्धारित करेगा कि आपको प्रदान करने की आवश्यकता है या नहीं
एक सीएलए और पीआर को उचित रूप से सजाएं (जैसे, स्थिति जांच, टिप्पणी)। बस निर्देशों का पालन करें
बॉट द्वारा प्रदान किया गया. आपको हमारे सीएलए का उपयोग करके सभी रेपो में केवल एक बार ऐसा करने की आवश्यकता होगी।

इस प्रोजेक्ट ने [Microsoft ओपन सोर्स आचार संहिता](https://opensource.microsoft.com/codeofconduct/) को अपनाया है।
अधिक जानकारी के लिए, [आचार संहिता FAQ](https://opensource.microsoft.com/codeofconduct/faq/) देखें या
किसी भी अतिरिक्त प्रश्न या टिप्पणी के लिए [opencode@microsoft.com](mailto:opencode@microsoft.com) से संपर्क करें।

## योगदानकर्ताओं की दीवार
<a href="https://github.com/microsoft/autogen/graphs/contributors">
<img src="https://contrib.rocks/image?repo=microsoft/autogen" />
</a>

# कानूनी नोटिस

Microsoft और कोई भी योगदानकर्ता आपको Microsoft दस्तावेज़ीकरण और अन्य सामग्री के लिए लाइसेंस प्रदान करते हैं
[क्रिएटिव कॉमन्स एट्रिब्यूशन 4.0 इंटरनेशनल पब्लिक लाइसेंस](https://creativecommons.org/licenses/by/4.0/legalcode) के तहत इस रिपॉजिटरी में,
[लाइसेंस](लाइसेंस) फ़ाइल देखें, और आपको [एमआईटी लाइसेंस](https://opensource.org/licenses/MIT) के तहत रिपॉजिटरी में किसी भी कोड के लिए लाइसेंस प्रदान करें, देखें
[लाइसेंस-कोड](लाइसेंस-कोड) फ़ाइल।

Microsoft, Windows, Microsoft Azure, और/या दस्तावेज़ में संदर्भित अन्य Microsoft उत्पाद और सेवाएँ
संयुक्त राज्य अमेरिका और/या अन्य देशों में Microsoft के ट्रेडमार्क या पंजीकृत ट्रेडमार्क हो सकते हैं।
इस प्रोजेक्ट के लाइसेंस आपको किसी भी Microsoft नाम, लोगो या ट्रेडमार्क का उपयोग करने का अधिकार नहीं देते हैं।
Microsoft के सामान्य ट्रेडमार्क दिशानिर्देश http://go.microsoft.com/fwlink/?LinkID=254653 पर पाए जा सकते हैं।

गोपनीयता जानकारी https://privacy.microsoft.com/en-us/ पर पाई जा सकती है

Microsoft और कोई भी योगदानकर्ता अन्य सभी अधिकार सुरक्षित रखते हैं, चाहे वे उनके संबंधित कॉपीराइट, पेटेंट के अंतर्गत हों।
या ट्रेडमार्क, चाहे निहितार्थ से, रोक से, या अन्यथा।

