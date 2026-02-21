Here is the complete and detailed English translation of the provided document, formatted in Markdown as requested:

# Project Document Translation

## Table of Contents

| Title | Section | Page |
| --- | --- | --- |
| **Introduction** | **1** | **4** |
| Project Notes and Rules | 1.1 | 4 |
| Evaluation Criteria | 1.2 | 4 |
| Checkpoints | 1.3 | 5 |
| First Checkpoint | 1.3.1 | 5 |
| Second Checkpoint | 1.3.2 | 5 |
| Project Report | 1.4 | 5 |
| Project Execution Guide | 1.5 | 5 |
| **General Project Overview** | **2** | **6** |
| Initial Explanations | 2.1 | 6 |
| User Levels | 2.2 | 6 |
| Project Tech Stack | 2.3 | 7 |
| **Project Details** | **3** | **8** |
| Police Ranks | 3.1 | 8 |
| Cadet | 3.1.1 | 8 |
| Coroner | 3.1.2 | 8 |
| Police Officer and Patrol Officer | 3.1.3 | 8 |
| Detective | 3.1.4 | 8 |
| Sergeant | 3.1.5 | 8 |
| Captain | 3.1.6 | 8 |
| Police Chief | 3.1.7 | 8 |
| Crime Levels | 3.2 | 8 |
| Level 3 | 3.2.1 | 8 |
| Level 2 | 3.2.2 | 8 |
| Level 1 | 3.2.3 | 9 |
| Critical Level | 3.2.4 | 9 |
| **Flows (Processes)** | **4** | **10** |
| Registration and Login | 4.1 | 10 |
| Case Creation | 4.2 | 10 |
| Case Creation via Complaint Registration | 4.2.1 | 10 |
| Case Creation via Crime Scene Registration | 4.2.2 | 10 |
| Evidence Registration | 4.3 | 11 |
| Witness or Local Testimonies | 4.3.1 | 11 |
| Found Evidence: Biological and Medical | 4.3.2 | 11 |
| Found Evidence: Vehicles | 4.3.3 | 11 |
| Found Evidence: ID Documents | 4.3.4 | 11 |
| Found Evidence: Other Items | 4.3.5 | 11 |
| Solving the Case | 4.4 | 11 |
| Suspect Identification and Interrogation | 4.5 | 11 |
| Trial | 4.6 | 12 |
| Suspect Status | 4.7 | 12 |
| Bounty | 4.8 | 12 |
| Paying Bail and Fines (Optional) | 4.9 | 12 |
| **Required Pages** | **5** | **13** |
| Main Page (Home) | 5.1 | 13 |
| Login and Registration Page | 5.2 | 13 |
| Modular Dashboard | 5.3 | 13 |
| Detective Board | 5.4 | 13 |
| Most Wanted | 5.5 | 13 |
| Case and Complaint Status | 5.6 | 14 |
| General Reporting | 5.7 | 14 |
| Evidence Registration and Review | 5.8 | 14 |
| **First Checkpoint Evaluation Criteria** | **6** | **15** |
| **Second Checkpoint Evaluation Criteria** | **7** | **17** |
| **Related Tutorials** | **8** | **18** |
| Designing and Implementing Responsive Pages | 8.1 | 18 |
| Implementing Access Levels in Django | 8.2 | 18 |
| Backend Testing | 8.3 | 18 |
| Frontend Testing | 8.4 | 18 |
| Pipeline Design and Creation | 8.5 | 19 |
| CI/CD | 8.6 | 19 |
| Test Payment Gateways | 8.7 | 19 |
| <br>(Table compiled based on )

 |  |  |

---

Chapter 1: Introduction 

1.1 Project Notes and Rules 

* Be sure to read all pages of this document before proceeding with the project.


* The development stack for this project is Django REST Framework for the backend and React or NextJS for the frontend.


* The use of any other framework will not be accepted.


* The project will be done in groups of three and will be delivered across 2 checkpoints.


* The first checkpoint of the project is backend development with DRF.


* The second checkpoint of the project is frontend development with React or NextJS.


* The upcoming document contains all the necessary explanations for completing both checkpoints.


* Despite the guidance provided in this document, requirements gathering and critical project decisions to develop a maintainable system are your responsibility.


* The project requires a final report that will be submitted in PDF format or via a GitHub/GitLab Wiki.


* The report itself has no standalone grade, but its existence is the primary condition for earning the project's points (8 points).


* The use of artificial intelligence is allowed, but pay close attention to the reporting section of this chapter.



1.2 Evaluation Criteria 

Each checkpoint, as well as the final delivery, will be evaluated based on the following criteria:

* 1. Fulfilling the requirements stated in the project document.


* 2. Clean and maintainable code, adhering to the principles taught in class.


* 3. Complete mastery of the project code by all members.


* 4. Participation of all members.



Please note that for the final delivery, a comprehensive written report of the project will also be required. We will detail this further in this document; additionally, delivery times for each checkpoint will be announced later. Most importantly, the basis for your participation in the project will be the number of commits you have in the project repository. A minimum of fifteen commits is required to earn the grade for each checkpoint. Naturally, your project's code repository (or repositories) must be public and accessible.

1.3 Checkpoints 

**1.3.1 First Checkpoint**
In the first checkpoint, only the backend of the project will be evaluated. Every required endpoint must be implemented with proper error handling, appropriate access level management, and strict adherence to REST principles and software engineering standards.

**1.3.2 Second Checkpoint**
In the second checkpoint, the frontend of the project—connected to the backend—will be evaluated. Note that due to reasons like incorrect initial requirements gathering, new requirements for frontend development, or a change in fundamental decisions, a need to modify the backend might arise. Making these changes is not a problem and is actually encouraged. Also, if you achieved at least 80 percent of the grade from the first checkpoint, you can deliver the remaining 20 percent during the second checkpoint.

1.4 Project Report 

First and foremost, it is highly recommended not to leave this report for the very end of the project. Instead, write it step-by-step as you develop the project within your GitLab or GitHub Wiki, or organize the whole thing using Obsidian (a powerful Markdown documentation software) and export it as a PDF. Your report must include the following:

* The responsibilities and tasks completed by each member.


* Development conventions (naming rules, commit message formats, etc.).


* Project management approach (how tasks were generated and divided).


* The key entities of the system along with the reasoning for their existence.


* A maximum of 6 NPM packages used in the project, including a summary of their function and a justification for their use.


* Several examples of AI-generated code.


* The strengths and weaknesses of artificial intelligence in frontend development.


* The strengths and weaknesses of artificial intelligence in backend development.


* Initial and final project requirement analyses, alongside the pros and cons of the decisions made regarding them.



Note that your report will be reviewed for consistency with the actual project. Any inconsistency between the report and the project will be considered as non-delivery of the report.

1.5 Project Execution Guide 

For the first checkpoint, we recommend starting by designing the entity models. The entire infrastructure of the system is built upon these models and their relationships, and any weakness or oversimplification at this stage will multiply costs in complex flows like case creation, evidence registration, case solving, and role management. Models must be precise, perfectly aligned with the document's requirements, and maintainable. Then, Endpoints should be built based on this design, not the other way around. Following REST principles, proper access management, good debugging, and providing complete Swagger documentation are unavoidable parts of this checkpoint. The evaluation criterion for this phase is that the backend must be unambiguous, clean, testable, and completely ready to connect to the frontend.

In the second checkpoint, your focus must be on precise, efficient, and modular UI implementation. However, this only makes sense if it relies on a standard backend infrastructure from the first checkpoint. All pages must align with requirements, be role-based, responsive, and logically sound from a UI/UX perspective. Complex flows like the detective board, case statuses, showing the most wanted, and the admin panel must function without placing heavy extra loads on the backend. This phase requires proper state management, loading displays, frontend testing, full project dockerization, and adherence to engineering patterns when building components. Output quality is acceptable when the frontend can smoothly and transparently present the project scenarios to the user without requiring drastic backend alterations.

---

Chapter 2: General Project Overview 

2.1 Initial Explanations 

You have likely heard of the game L.A. Noire by Rockstar Games. In this game, you play the role of a detective solving criminal cases in Los Angeles. Because the game is set in the late 1940s, almost all police department tasks happen manually on paper. Now, in the year 2025, the city's police department has decided to automate its operations and store data on machines. To this end, the department's requirements are provided to you in this document, and you are tasked with creating a web-based system for the department that meets these needs. Additionally, the flows and access levels involved in them will be discussed in this document.

2.2 User Levels 

The base roles of users generally fall into the following categories:

* System Administrator 


* Police Chief 


* Captain 


* Sergeant 


* Detective 


* Police Officer and Patrol Officer 


* Cadet 


* Complainant and Witness 


* Suspect and Criminal 


* Judge 


* Coroner 


* Base User 



Keep in mind that without needing to change the code, the system administrator must be able to add a new role, delete existing roles, or modify them.

2.3 Project Tech Stack 

We have designated the following tech stack for this project:

* React or NextJS for the frontend.


* Django REST Framework for the backend.


* PostgreSQL as the recommended database.



---

Chapter 3: Project Details 

3.1 Police Ranks 

* 
**3.1.1 Cadet**: The Cadet is the lowest-ranking employee in the police department. The main duty of the Cadet is the initial filtering and verification of received complaints; if there are no issues, they forward it to higher ranks to open a case.


* 
**3.1.2 Coroner**: The Coroner is responsible for examining and either verifying or rejecting biological and medical evidence.


* 
**3.1.3 Police Officer and Patrol Officer**: Police and patrol officers are tasked with field activities, reporting any suspicious phenomena or crimes they encounter in order to create a case.


* 
**3.1.4 Detective**: The primary responsibility for searching for evidence and reasoning connections between them lies with the Detective. After analyzing a case, the Detective identifies the suspects and reports them to the Sergeant. The Detective also assists the Sergeant in the interrogation process and drawing conclusions from it.


* 
**3.1.5 Sergeant**: The Sergeant is the primary partner and supervisor of the Detective in solving a case. The Sergeant issues arrest warrants and interrogates suspects. The Sergeant determines the probability of the suspects being guilty and reports the result to the Captain or the Police Chief.


* 
**3.1.6 Captain**: The Captain's duty is to approve the case and forward it to the judiciary system so that a trial can take place.


* 
**3.1.7 Police Chief**: In critical crimes, the Police Chief refers the suspects to the judiciary for trial instead of the Captain.



3.2 Crime Levels 

* 
**3.2.1 Level 3**: Minor crimes such as petty theft and minor fraud fall into this category.


* 
**3.2.2 Level 2**: Larger crimes like auto theft are placed in this category.


* 
**3.2.3 Level 1**: Major crimes such as murder are located here.


* 
**3.2.4 Critical Level**: Macro crimes like serial killings or the assassination of a VIP figure are placed here.



---

Chapter 4: Flows (Processes) 

4.1 Registration and Login 

First, every user creates an account in the system with a "base user" role by setting at least a username, password, email, phone number, full name, and national ID. Then, the system administrator grants each user the roles they require. Roles are dynamic; new roles can be created, and existing roles can be deleted. Logging into the system will be done using the password and one of the following: username, national ID, phone number, or email. Naturally, all these fields must be unique.

4.2 Case Creation 

A case begins to form either when a complainant registers a complaint or when a police rank (other than a Cadet) witnesses a crime scene or receives a report about one and wishes to register it.

**4.2.1 Case Creation via Complaint Registration** First, the complainant logs into the system and requests to open a case via the site menus. There, they enter the case information and perform an initial submission. This information then goes to a Cadet rank for review. If all the entered information is deemed accurate by the Cadet, the Cadet must forward the case to their superior, a Police Officer. If everything is correct after the Police Officer's review, the case is created. Note the following:

* If the Cadet finds a defect in the case, they send it back to the complainant to fill out again.


* When returning the case to the complainant, it must include an error message written by the Cadet.


* If the Police Officer finds a flaw in the case, it does not go directly back to the complainant; instead, it goes back to the Cadet for a re-review.


* If the complainant submits incomplete or false information in the case 3 times, the case is voided and will no longer be forwarded to police ranks for review.


* A case might have multiple other complainants. The information of the complainants will be approved or rejected by the Cadet.



**4.2.2 Case Creation via Crime Scene Registration** First, a police rank (other than a Cadet) witnesses a crime scene or it is reported to them by local witnesses. In this type of case:

* The police log the crime scene along with the time and date in the case file.


* The phone number and national ID of witnesses are recorded in the case for future follow-ups.


* In this scenario, only one superior rank needs to approve the case; if the Police Chief registers it, no one's approval is needed.


* Initially, these cases do not have a complainant, but a number of complainants can gradually be added to it.



4.3 Evidence Registration 

Evidence is divided into two categories, which we will discuss further. Key notes for this section are:

* All evidence includes a title and a description.


* All evidence must have a registration date.


* All evidence has a registrar (a person who logs it).



**4.3.1 Witness or Local Testimonies**
One can include a transcript of the witnesses' statements regarding the case. Additionally, locals might have images, videos, or audio related to the incident.

**4.3.2 Found Evidence: Biological and Medical**
At the crime scene, evidence might be found that requires forensic examination. For example, a bloodstain, a strand of hair, or a fingerprint must be examined and verified either by the coroner or the national identity database. These items must be saved with a title, description, and one or more images. Also, the result of the follow-up from the coroner or database is initially empty but can be filled in later.

**4.3.3 Found Evidence: Vehicles**
A vehicle connected to the crime scene might be found in the area. Its model, license plate, and color must be registered as evidence. If a vehicle lacks a license plate, its serial number must be entered. Note that when saving this type of evidence, the license plate number and the serial number cannot both have a value at the same time.

**4.3.4 Found Evidence: ID Documents**
An ID document belonging to a suspect might be found at the crime scene. In this case, it must be possible to save the full name of the document's owner along with other details of the document (in a key-value format). These key-value pairs do not have a fixed quantity and might even not exist at all (for instance, it might be an ID card with only a person's name on it).

**4.3.5 Found Evidence: Other Items**
Other evidence must be recorded as a title-description record.

4.4 Solving the Case 

After creation, a case can be reviewed by a Detective. The Detective has a "Detective Board" where documents and evidence are placed (anywhere the Detective desires). The Detective can then connect related documents with a red line. Next, the Detective declares the main suspects of the case to the Sergeant and waits for approval. The Sergeant reviews the available evidence and matches the Detective's reasoning with the suspects' records. If approved, a confirmation message goes to the Detective and the arrest of suspects begins. If the Sergeant objects, the objection is returned as a message to the Detective, and the case remains open. Note that new documents and evidence can be added while a case is being solved; for each one, a notification must be sent to the Detective.

4.5 Suspect Identification and Interrogation 

After their arrest, suspects are interrogated by the Sergeant and the Detective. Both the Sergeant and the Detective assign a probability of the suspect's guilt from 1 to 10 (lowest to highest). Their scores are then sent to the Captain, who gives the final verdict using their statements, the evidence, and the recorded scores. In critical level crimes, the Police Chief must also approve or reject the Captain's decision.

4.6 Trial 

A guilty person must go to court. The Judge must have access to the entire case file, the evidence, and all police members involved in the case, complete with full details of all mentioned entities. This also includes every approved or rejected report and their specifics. The final verdict of guilty or innocent is then logged by the Judge, and if guilty, the punishment is recorded by them with a title and description.

4.7 Suspect Status 

From the moment someone is identified as a suspect in a case, they are placed in a "Wanted" status. Suspects who have been wanted for over a month are placed in the "Most Wanted" status, and their photos and details are placed on a page visible to all users.

* **Note 1:** The ranking on the Most Wanted page will be calculated as follows:


Which means the product of the maximum days they have been wanted for a single crime in an open case, multiplied by the highest crime degree (from 1 to 4, for level three up to critical) they have committed so far (across open or closed cases).


* **Note 2:** Below the info of each person in this category, a bounty for any information leading to them must be registered. This bounty is calculated using the following formula:


This amount is in Rials.



4.8 Bounty 

A normal user logs into the system and registers information regarding a case or a suspect. A police officer does an initial review of this information. If the provided info is completely invalid, they reject it; otherwise, the info is sent to the Detective in charge of the case. If the Detective verifies this information, the user is notified that their information was useful and is given a Unique ID. They can go to the police station and present the reward code to receive their bounty. Additionally, all police ranks must be able to enter the person's national ID and unique code to view the bounty amount along with the related user's information.

4.9 Paying Bail and Fines (Optional) 

Suspects of Level 2 and Level 3 crimes, as well as Level 3 criminals (pending the Sergeant's approval), can be released from custody by paying bail and fines. (The amount is determined by the Sergeant) . For this purpose, your system must be connected to a payment gateway.

---

Chapter 5: Required Pages 

5.1 Main Page (Home) 

On this page, you must provide a general introduction to the system as well as the police department and their duties. On the home page, you should display several statistics (at least three) regarding cases and their statuses. We recommend the following three items:

* Total number of solved cases 


* Total number of organization employees 


* Number of active cases 



5.2 Login and Registration Page 

There must be a dedicated login and registration page through which a user can sign in or register an account in the system.

5.3 Modular Dashboard 

You must show an appropriate dashboard for every user account. Your dashboard must be modular. This means the main page will display a set of modules (for example: auditing, case review, complaint review, etc.) to the user based on their access level. For instance, a Detective must see the "Detective Board" module on their dashboard, but the Coroner should not see such a module on theirs.

5.4 Detective Board 

The Detective Board must contain a number of documents or notes. These documents and notes can be connected to each other with a red line. The placement of these documents and notes must be modifiable via drag-and-drop. The lines between documents must also be addable and removable. Additionally, it must be possible to export it as an image so the Detective can attach it to their report. As a guide, a sample of a real detective board is provided in the image below:
*(Image provided in original document)* 

5.5 Most Wanted 

On this page, you must display the criminals and suspects who are heavily wanted, along with the specified details about them.

5.6 Case and Complaint Status 

Every user, depending on their access levels and the stated rules, must view the cases and complaints relevant to them (i.e., those they have access to) and edit them if permitted. (This page is crucial in the mentioned flows for registering, editing, or deleting data from cases, as well as approving, rejecting, and altering statuses) .

5.7 General Reporting 

This page is primarily for the Judge, Captain, and Police Chief. On this page, you must present a complete report of every case, including creation date, evidence and testimonies, suspects if any, criminal, complainant(s), and the names and ranks of all individuals involved in it.

5.8 Evidence Registration and Review 

Based on the defined processes, you will create the ability to register and review evidence on this page for each user depending on their access level.

---

Chapter 6: First Checkpoint Evaluation Criteria 

The first checkpoint, which encompasses the project's backend, is out of 4750 points. The details are listed below. It is worth reiterating that obtaining the project grade inherently depends on the existence of the final report; its absence will result in losing the entire project grade (i.e., losing the 8 course points plus 1.5 bonus points). Also, note that a significant portion of your project grade is dedicated to the cleanliness of your code and technical details. So, follow this matter strictly and carefully to avoid losing points. Furthermore, your backend must have Swagger documentation (otherwise, it will not be graded).

* Logical and precise design of entity models according to requirements (750 pts).


* Presence of appropriate Endpoints to respond to the stated requirements (1000 pts).


* Presence of necessary CRUD APIs, no more than needed and no less (250 pts).


* Adherence to stated REST principles (100 pts).


* Access level verification and proper response in every API Call (250 pts).


* Implementation of suitable flow Endpoints (400 pts).


* Implementation of Role-Based Access Control (200 pts).


* Modifiability of roles (creating a new role, removing or modifying a previous role) without touching the code (150 pts).


* Creation of efficient and suitable Endpoints for flows (1100 pts):


* Registration and Login (100 pts).


* Case Creation (100 pts).


* Evidence Registration (100 pts).


* Case Solving (Design the Detective Board backend so minimal changes are needed in CP2) (200 pts).


* Suspect Identification and Interrogation (100 pts).


* Trial (100 pts).


* Suspect Status (100 pts).


* Bounty (100 pts).


* Payment (Connection to payment gateway is important) (200 pts).




* Presence of Endpoints for fetching aggregated and general statistics (200 pts).


* Correct implementation of suspect and criminal ranking (300 pts).


* Presence of a payment gateway callback page (using Django Templates is recommended) (100 pts).


* Dockerizing the backend project and its utilized services (200 pts).


* Completeness and reliability of Swagger docs (having proper request/response examples and full descriptions) (250 pts).


* Presence of at least 5 tests in two different apps (at least 10 tests total) (100 pts).


* Clean code and adherence to best practices taught in the course (100 pts).


* Breaking the backend into a reasonable number of apps (not too many, not too few) (100 pts).


* Utilizing built-in capabilities of Django and DRF as much as possible, and avoiding boilerplate code (100 pts).


* Ease of modifying code (adding features or modifying existing ones) (100 pts).



---

Chapter 7: Second Checkpoint Evaluation Criteria 

In the second checkpoint, the project's frontend will be evaluated. Naturally, you have the right to modify the backend code (in pursuit of a better infrastructure for the frontend implementation). However, try to use the CP1 backend as much as possible. Again, technical details and code cleanliness matter heavily in this phase, and poor code quality will not be overlooked. Once more, it is emphasized that at the end of the second checkpoint, you are obligated to upload the final project report. Otherwise, you will lose the entire project grade, and no excuses will be accepted.

The checklist for this checkpoint is as follows:

* Proper UI/UX implementation of pages (precise functionality matching requirements) (3000 pts):


* Home Page (200 pts).


* Login and Registration Page (200 pts).


* Modular Dashboard (800 pts).


* Detective Board (800 pts).


* Most Wanted (300 pts).


* Case and Complaint Status (200 pts).


* General Reporting (300 pts).


* Evidence Registration and Review (200 pts).


* Admin Panel (non-Django but with similar functionality) (200 pts).




* Displaying loading states and Skeleton Layout (300 pts).


* Dockerizing the entire project and using Docker Compose (300 pts).


* Presence of at least 5 tests in the frontend section (100 pts).


* Proper state management (100 pts).


* Responsive Pages (300 pts).


* Adherence to best practices taught in class and slides (150 pts).


* Implementing and accounting for component lifecycles properly (100 pts).


* Displaying appropriate error messages corresponding to each situation (100 pts).


* Ease of code modifiability (100 pts).



---

Chapter 8: Related Tutorials 

Several links for further learning are provided below:

8.1 Designing and Implementing Responsive Pages 

* MDN Documentation — Media Queries 


* web.dev Responsive Design Guide 


* CSS Tricks Flexbox Guide 


* Dribbble 



8.2 Implementing Access Levels in Django 

* Concept of RBAC 


* A simple example of RBAC implementation in Django 


* MDN Documentation - Permissions 


* Authentication and Access Control - Django 


* Permissions in DRF 



8.3 Backend Testing 

* Python Unittest Documentation 


* Pytest Guide 


* Django Testing Tutorial 


* DRF Tests 



8.4 Frontend Testing 

* React Testing Library 


* Jest JavaScript Testing 


* Playwright 



8.5 Pipeline Design and Creation 

* GitLab CI/CD Pipelines 


* GitHub Actions Documentation 


* CI/CD with Docker 



8.6 CI/CD 

* Continuous Integration — Atlassian 


* Continuous Delivery — ThoughtWorks 



8.7 Test Payment Gateways 

* ZarinPal 


* IDPay 


* BitPay 



---

Would you like me to help you brainstorm the initial database schema or map out the component tree based on these requirements?