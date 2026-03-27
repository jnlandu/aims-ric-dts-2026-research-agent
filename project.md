**Project 4** 

**Research Assistant: Building a Multi-Agent Assistant for Search, Evidence Synthesis and Report Writing**

***Starter Notebook*****: From scratch (based on your learnings in LLM Agents)**

**Project Background**

Researchers, analysts, consultants, and policy professionals often need to work across many sources to answer complex questions. In practice, this involves more than simply retrieving information. A good research workflow usually requires several stages:

* finding relevant and credible sources  
* extracting important claims and supporting evidence  
* comparing agreements and disagreements across sources  
* organizing findings into themes  
* communicating conclusions clearly while acknowledging uncertainty

A single-step response from a language model may sound fluent, but it is often not sufficiently transparent, structured, or reliable for serious research tasks. For this reason, modern AI systems are increasingly being designed as **multi-agent workflows**, where different components specialize in different parts of the problem.  
In this project, students will build a **multi-agent research assistant** that behaves like a small junior research team. The system will include three main agents:

* **SearchAgent**: identifies sources and extracts relevant evidence  
* **SynthesisAgent**: organizes evidence into themes, compares perspectives, and resolves or highlights contradictions  
* **ReportAgent**: produces a structured, evidence-backed report with citations, limitations, and careful wording

The goal is not only to produce a report but also to help students understand how **modular AI systems** can support research, policy analysis, technical review, and evidence-informed decision-making.

**Project Aim**

This project aims to design and implement a **multi-agent research pipeline** that can transform a research question into a structured report supported by traceable evidence.  
Your system should be able to:

* Accept a research prompt  
* Gather relevant sources  
* Extract useful evidence from those sources  
* Organise evidence into themes or arguments  
* Identify where sources agree or differ  
* Generate a final report with citations and limitations  
* Evaluate the quality of its own output using a defined rubric

Students should approach this project as a **small research systems engineering task**, with emphasis on:

* transparency  
* evidence fidelity  
* modular system design  
* responsible synthesis  
* clear academic communication

**What Students Are Expected to Learn**

By completing this project, students should develop a practical understanding of:

* How multi-agent systems differ from single-step prompting  
* How research workflows can be decomposed into coordinated stages  
* How to structure shared memory or shared state across agents  
* How to track claims and link them back to evidence  
* How to assess report quality in terms of coverage, faithfulness, and hallucination  
* How to write research outputs that are both useful and transparent

This project is especially valuable because it sits at the intersection of:

* **LLMs and agentic AI**  
* **information retrieval**  
* **evidence synthesis**  
* **research automation**  
* **responsible AI reporting**

**Recommended Use Cases**

Students must test the system on **two different prompts**, one from a more technical domain and one from a policy, business, or applied decision-making domain.  
Examples of **technical prompts** might include:

* What are the main trade-offs between CNNs and Vision Transformers for medical imaging?  
* How is retrieval-augmented generation evaluated in current NLP research?  
* What are the major challenges in multimodal learning for low-resource settings?

Examples of **policy or business prompts** might include:

* What are the opportunities and risks of adopting AI in higher education institutions?  
* How can digital agriculture platforms support smallholder farmers in Africa?  
* What are the policy implications of using AI tools in public health monitoring?

Students should explain why the two prompts were chosen and how the system behaves across different domains.

**Multi-Agent System Design**

The system must include at least the following three agents.

**Agent 1: SearchAgent**

The SearchAgent is responsible for finding relevant sources and extracting evidence related to the research question.  
Its main functions include:

* generating or refining search queries  
* retrieving sources  
* selecting potentially useful content  
* extracting snippets, notes, or evidence fragments  
* recording source metadata such as title, URL, access time, and credibility notes

The SearchAgent should not simply gather many links. It should aim to collect **relevant and evidence-rich materials** that can support later synthesis.

**Agent 2: SynthesisAgent**

The SynthesisAgent is responsible for making sense of the collected evidence.  
Its role includes:

* grouping evidence into themes  
* identifying recurring ideas across sources  
* recognizing disagreement or contradiction  
* merging related evidence into coherent claims  
* assigning confidence levels where appropriate

This is one of the most important parts of the project because it teaches students that research is not only about collecting facts but also about **organizing and interpreting evidence carefully**.

**Agent 3: ReportAgent**

The ReportAgent is responsible for writing the final report in a structured and readable form.  
Its tasks include:

* drafting a clear outline  
* converting synthesized evidence into well-phrased report sections  
* ensuring that major claims are supported by citations  
* including limitations, caveats, and uncertainty  
* producing a final report in markdown or exportable format

The ReportAgent should not invent unsupported conclusions. It must remain grounded in the evidence passed from earlier stages.

**Shared State and Agent Communication**

A central requirement of this project is the use of a **shared state object** that allows agents to coordinate.  
Students must define a structured shared state that holds information such as:

* the research question  
* search queries used  
* retrieved sources  
* extracted snippets or notes  
* draft claims  
* grouped themes  
* report outline  
* Final report text  
* evaluation scores or reflections

This is essential because multi-agent systems are not just separate prompts; they require **controlled information flow** between components.  
A strong implementation should make it easy to inspect:

* What each agent added  
* What evidence supports each claim  
* How the report was assembled

**Project Workflow**

Students should implement the project as a full pipeline rather than isolated agent demos.

**Stage 1: Define the Research Question**

Begin by clearly stating the research question or prompt.  
Students should explain:

* Why the question matters  
* What kind of answer is expected  
* What counts as useful evidence  
* whether the task is exploratory, comparative, or decision-oriented

This helps constrain the work of the agents.

**Stage 2: Source Discovery and Evidence Collection**

The SearchAgent should retrieve sources relevant to the question and record useful information from them.  
At a minimum, the system should track:

* source title  
* source URL  
* time accessed  
* credibility or quality notes  
* extracted snippets or evidence

Students should discuss how sources are chosen and whether some source types are prioritised over others.

**Stage 3: Evidence Organisation and Contradiction Handling**

The SynthesisAgent should review collected evidence and organise it into themes.  
Students should ensure the system can handle cases such as:

* Multiple sources making the same claim  
* sources addressing different parts of the question  
* disagreement across sources  
* incomplete or uncertain evidence

A strong system should not hide disagreement. Instead, it should make contradictions visible and explain them carefully.

**Stage 4: Report Generation**

The ReportAgent should transform organized evidence into a clear final report.  
A strong report should include:

* title  
* Introduction or context  
* thematic findings  
* discussion of agreements and disagreements  
* limitations  
* conclusion  
* references

Every major claim should be linked to at least one source.

**Final Report**

The report is a PDF document that is ready for export.

**Stage 5: Evaluation and Reflection (Bonus, Optional)**

Students must not stop at report generation. They must also evaluate the quality of the system’s output.  
The project should include a scoring rubric covering:

* **Coverage: Did** the report address the key parts of the question?  
* **Faithfulness**: Are claims supported by evidence?  
* **Hallucination rate**: how many claims appear unsupported or overstated?  
* **Usefulness/actionability**: is the final output clear, relevant, and decision-supportive?

Students should apply this rubric to both prompts and reflect on system strengths and weaknesses.

