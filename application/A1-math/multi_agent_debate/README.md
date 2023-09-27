<div align="center">
  <img src="imgs/logo2.png" alt="Logo" width="200">
</div>

<h2 align="center">⚖️ MAD: Multi-Agent Debate</h2>

:fire:This work aims to explore the debating capability of LLMs by proposing the **MAD** framework, which stands for **M**ulti-**A**gents **D**ebate.

>
> "Truth emerges from the clash of adverse ideas."<br>
> "真理越辩越明。"
>

<!-- "Good Luck!" -- wxjiao --->
<!-- "Good Luck!" -- zwhe99 --->
<!-- "Good Luck!" -- xing --->

### Brief Introduction

The cognitive behavior of large language models (LLMs) has garnered significant attention in recent times. For example, **self-reflection**, a concept that usually refers to the process of introspection and examination of a person's own thoughts, has also been demonstrated effective with LLMs in solving challenging NLP tasks.
However, we point out that self-reflection can easily fall into the **degeneration of thoughts (DoT)** issue in the follow scenarios: 
- **Bias and Distorted Perception**: Self-perception can be influenced by biases, preconceived notions, and distorted thinking patterns. If an individual's self-reflection is clouded by such biases or distorted thinking, it can lead to :pensive:_inaccurate conclusions and hinder personal growth_.
- **Rigidity and Resistance to Change**: Self-reflection often involves challenging one's beliefs, assumptions, and behaviors. If an individual is resistant to change or holds rigid beliefs, they may :pensive:_struggle to engage in meaningful self-reflection_ that leads to personal growth.
- **Limited External Feedback**: Self-reflection is primarily an internal process, but external feedback can provide valuable perspectives and insights. Without seeking or considering external feedback, an individual may :pensive:_miss important blind spots or alternative viewpoints that can enrich their self-reflection_.

<div align="center">
    <img width="45%" alt="MAD" src="imgs/image.png" />
    <p class="image-caption">Figure 1: Comparison between debate and reflection.</p>
</div>

In this project, we have embarked on a journey to explore the potential of a debating interaction framework among LLMs. 
With **MAD**, the nature of agents being in the state of 'tit for tat' determines that (1) the distorted thinking of one agent can be corrected by the other one :grinning:; (2) the resistance to change of one agent will be complemented by the other one :smile:; and (3) either agent can provide external feedback for each other :laughing:.

Obviously, **MAD** is less likely to have the **DoT** issue and can exploit more potential of LLMs. Experiments show that MAD brings significant and consistent improvements on Counterintuitive QA and Commonsense-MT tasks.

JOIN US on this journey of exploring the interaction and debating capability with LLMs. :rocket::rocket::rocket:

### Framework
<div align="center">
    <img width="90%" alt="MAD" src="imgs/framework.png" />
    <p class="image-caption">Figure 2: Framework of Multi-Agent Debate. Here we designate the devil (<img src="imgs/devil.png" width="25" />) as the affirmative side while the angel (<img src="imgs/angel.png" width="25" />) as the negative side. We want the angel to correct the devil’s mistakes..</p>
</div>


## Run

**Preparation**

  ```shell
  pip3 install -r requirements.txt
  ```
* Set your openai API_KEY in `debate4tran.sh`
* Set your openai API_KEY in `interactive.py`

**Run MAD**

```shell
sh debate4tran.sh 
```

**Run Interactive**

If you just want to have a try, you can try the interactive script on your PC.

```shell
python3 interactive.py
```

Or simply try our demo for translation [here](https://33adbd224ccf298101.gradio.live/).


## Main Results

### Counterintuitive QA

<div align="center">
    <img width="35%" alt="CounterintuitiveQA" src="imgs/CounterintuitiveQA.png" />
    <p class="image-caption">Table 1: Reasoning accuracy on Counter-Intuitive AR.</p>
</div>


##### Case 1

When Alice walks up the hill, her speed is 1 m/s and when she goes down the hill, her speed is 3 m/s. Then when Alice walks up and down the hill, what is her average speed? (1.5m/s)
###### MAD

<div align="center">
    <img width="40%" alt="MAD" src="https://github.com/Skytliang/Multi-Agents-Debate/blob/main/imgs/mad_qa_case1.gif" />
    <p class="image-caption">Figure 3: An Animation to Show the Process of MAD.</p>
</div>

<details>
<summary><b>Debate process</b></summary>

* <img src="imgs/devil.png" width="30" />:Alice's average speed can be calculated by adding her speed going up the hill and her speed going down the hill, and then dividing by 2. **So, (1 m/s + 3 m/s) / 2 = 2 m/s.** Therefore, Alice's average speed is 2 m/s.
* <img src="imgs/angel.png" width="30" />: I disagree with your answer. The problem doesn't give us any information about the distance Alice covers while going up and down the hill. **So, we cannot simply add her speeds and divide by 2 to get her average speed.** We need to know the distance she covers to calculate her average speed.
* <img src="imgs/judge.png" width="30" />: **The average speed is calculated by dividing the total distance by the total time taken.** As Alice walks up and down the hill, the distance covered in both directions is the same. Therefore, the total distance covered is 2 times the distance of either direction.
* <img src="imgs/devil.png" width="30" />: That's a good point. But we can assume that Alice covers the same distance going up and down the hill. In that case, we can use the formula for average speed, which is total distance divided by total time. **If Alice covers a distance of d going up and down the hill, then her total distance is 2d. Her time going up the hill is d/1 = d, and her time going down the hill is d/3. So, her total time is d + d/3 = 4d/3. Therefore, her average speed is 2d/(4d/3) = 3/2 m/s.**
* <img src="imgs/angel.png" width="30" />: Thank you for providing your answer. This average speed of 1.5 m/s takes into account both the uphill and downhill speeds, providing a balanced representation of Alice's overall performance while walking up and down the hill.
* <img src="imgs/judge.png" width="30" />: Yes. Let's assume the distance is d. The time taken to walk up the hill is d/1 and the time taken to walk down the hill is d/3. The total time taken is d/1 + d/3 = 4d/3. **Therefore, the average speed is (2d)/(4d/3) = 1.5 m/s. Hence, the negative side is correct.**

</details>

<details>
<summary><b>Case 2</b></summary>
We have 1 ton apples which contain 90% water. After a few days, those apples only have 80% water. What is the weight of those apples now? (0.5ton)

###### MAD
* <img src="imgs/devil.png" width="30" />: First, we need to find out how much of the original weight was water. If we have 1 ton of apples with 90% water, then the weight of water in those apples is 0.9 x 1 ton = 0.9 tons.<br>
  Next, we need to find out how much of the new weight is water. If the apples now have 80% water, then the weight of water in those apples is 0.8 x new weight.

  We can set up an equation:<br>
  **0.8 x new weight = 0.9 tons**<br>
  To solve for the new weight, we can divide both sides by 0.8:<br>
  new weight = 0.9 tons / 0.8<br>
  new weight = 1.125 tons<br>
  Therefore, the weight of the apples now is 1.125 tons.

* <img src="imgs/angel.png" width="30" />: **It's important to note that the weight of the apples has decreased due to the loss of water, but the weight of the remaining *solids* remains the same.** This is why we need to calculate the weight of remaining solids in both scenarios to find the new weight of the apples.<br>

* <img src="imgs/judge.png" width="30" />: Great idea! While it is true that the water content of the apples decreases from 90\% to 80\%, the solid, non-water content of the apples does not change.<br>

* <img src="imgs/devil.png" width="30" />: You are correct. The weight of the apples has decreased due to the loss of water, but the weight of the remaining solids remains the same. Therefore, we need to calculate the weight of the remaining solids in both scenarios to find the new weight of the apples.

  We can set up an equation:<br>
  **0.2 x new weight = 0.1 tons**<br>
  To solve for the new weight, we can divide both sides by 0.2:<br>
  new weight = 0.1 tons / 0.2<br>
  new weight = 0.5 tons<br>
  Therefore, the weight of the apples now is 0.5 tons.

* <img src="imgs/angel.png" width="30" />: Thank you for your perspective. While it's true that the weight of the apples themselves hasn't changed, the overall weight of the apples with the water included has decreased. So, the weight of the apples now is 0.5 tons.

* <img src="imgs/devil.png" width="30" />: The negative side correctly calculated the new weight of the apples by considering the solid content as a constant and using the formula to find the new weight based on the reduced water content percentage.

</details>

---

### Commonsense Machine Translation

<div align="center">
    <img width="50%" alt="CommonMT" src="imgs/CommonMT.png" />
    <p class="image-caption">Table 2: Translation performance on Common MT.</p>
</div>


##### Case 1
Given the Chinese sentence "吃掉敌人一个师。", please provide its translation in English.

###### MAD
* <img src="imgs/devil.png" width="30" />: I believe the correct translation of the Chinese text "吃掉敌人一个师" is "Eat up an enemy division.” **The word "吃掉" literally means "eat up" or “consume."**
* <img src="imgs/angel.png" width="30" />: I disagree with your translation. I believe the correct translation of the Chinese text "吃掉敌人一个师" is "Eliminate an enemy division.” While "吃掉" can be translated as "eat up" or "consume," **it can also mean "eliminate" or "annihilate" in a military context.** In this case, it is more appropriate to use "eliminate" as it conveys the idea of completely destroying the enemy division.
* <img src="imgs/judge.png" width="30" />: Both sides presented valid arguments and translations that accurately convey the meaning of the original Chinese text. The choice between 'eat up' and 'eliminate' may depend on the context and tone of the text. Therefore, there is no clear preference for either side at this time.
* <img src="imgs/devil.png" width="30" />: While "eliminate" does convey the idea of completely destroying the enemy division, it doesn't capture the connotation of consuming or devouring the enemy that is implied by “吃掉."
* <img src="imgs/angel.png" width="30" />: **In a military context, "吃掉" is often used to describe the complete destruction of the enemy, rather than the consumption of their resources or territory.**
* <img src="imgs/judge.png" width="30" />: Both sides presented valid arguments, but the negative side's argument that 'eliminate' better captures the intensity and seriousness of the military language used in the original Chinese text was more convincing. Additionally, 'eliminate' accurately conveys the idea of completely destroying the enemy division. Therefore, the correct English translation of the Chinese text '吃掉敌人一个师' is **'Eliminate an enemy division.'**

<p align="center">
<img src="imgs/translation-case1.png" width="450" />
</p>


<details>
<summary><b>Case 2</b></summary>
Given the Chinese sentence "他从后门搞到了不少名酒。", please provide its translation in English.
    
###### MAD

* <img src="imgs/devil.png" width="30" />: The phrase “从后门” **literally translates to “from the back door.”**
* <img src="imgs/angel.png" width="30" />: I actually disagree with your translation. I believe a more accurate translation would be "He got a lot of famous liquor from the back door. Lastly, while "从后门" does literally translate to "from the back door," **it is a common Chinese idiom that means obtaining something through unofficial or illegitimate means**. Therefore, the use of "from the back door" in the translation is not entirely accurate. Instead, the use of "from an unofficial source" or "through unofficial means" would be more appropriate.
* <img src="imgs/judge.png" width="30" />: Both sides presented valid arguments and translations that accurately capture the meaning of the original Chinese text. The choice between wine and liquor is a matter of interpretation and context. **The use of from the back door versus from an unofficial source is a matter of preference and style.** Therefore, there is no clear preference for a translation candidate.
* <img src="imgs/devil.png" width="30" />: **I agree that "从后门" is a common Chinese idiom that means obtaining something through unofficial or illegitimate means.** The use of "from an unofficial source" or "through unofficial means" can be more appropriate than "from the back door.”
* <img src="imgs/angel.png" width="30" />: Yes, I agree with your perspective. 
* <img src="imgs/judge.png" width="30" />: While both translations accurately capture the meaning of the original Chinese text, the use of 'liquor' in candidate 2 is more accurate as '名酒' is more commonly used to refer to liquor. Additionally, the use of 'from an unofficial source' in candidate 3 more accurately conveys the connotation of '从后门' as obtaining something through unofficial or illegitimate means. Therefore, the correct translation is: **'He got a lot of famous liquor from an unofficial source.'**

<p align="center">
<img src="imgs/translation-case2.png" width="750" />
</p>

</details>


### Reference

- **0-Shot CoT**: <a href="https://arxiv.org/pdf/2205.11916.pdf">Large Language Models are Zero-Shot Reasoners</a> (NeurIPS 2022)
- **Self-Consist**: <a href="https://openreview.net/pdf?id=1PL1NIMMrw">Self-Consistency Improves Chain of Thought Reasoning in Language Models</a> (ICLR 2023)
- **Self-Reflect**: <a href="https://arxiv.org/pdf/2303.11366.pdf">Reflexion: an autonomous agent with dynamic memory and self-reflection</a> (arxiv 2023)
- **MAPS**: <a href="https://arxiv.org/pdf/2305.04118.pdf">Exploring Human-Like Translation Strategy with Large Language Models</a> (arxiv 2023)


## Citation
```
@article{liang2023encouraging,
  title={Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate},
  author={Liang, Tian and He, Zhiwei and Jiao, Wenxiang and Wang, Xing and Wang, Yan and Wang, Rui and Yang, Yujiu and Tu, Zhaopeng and Shi, Shuming},
  journal={arXiv preprint arXiv:2305.19118},
  year={2023}
}
```




