import React, { useState } from 'react';
import { FileText, Folder, Plus, X, Search, Loader2, BookOpen, Scale, Shield, FileCheck } from 'lucide-react';

const CasemindDemo = () => {
  const [activeTab, setActiveTab] = useState('FIR_Copy.pdf');
  const [chatMessages, setChatMessages] = useState([
    {
      type: 'system',
      content: 'Welcome to Casemind. I can help you analyze case documents, find similar cases, and suggest legal strategies.'
    }
  ]);
  const [savedCases, setSavedCases] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [chatInput, setChatInput] = useState('');

  const caseFiles = [
    { name: 'FIR_Copy.pdf', icon: FileText },
    { name: 'Medical_Examination_Report.pdf', icon: FileText },
    { name: 'Witness_Statements.pdf', icon: FileText },
    { name: 'Charge_Sheet.pdf', icon: FileText }
  ];

  const similarCases = [
    {
      id: 1,
      name: 'State vs Rajesh Sharma',
      year: '2020',
      court: 'Bombay High Court',
      similarity: '87%',
      description: 'Similar bail application involving IPC 304(ii), 323, 504. Defense successfully argued lack of intention and granted bail with conditions.'
    },
    {
      id: 2,
      name: 'State vs Priya Mehta',
      year: '2019',
      court: 'Delhi High Court',
      similarity: '82%',
      description: 'Comparable facts under IPC 306, 323. Court considered medical evidence and granted interim bail pending trial.'
    },
    {
      id: 3,
      name: 'State vs Vikram Singh',
      year: '2021',
      court: 'Gujarat High Court',
      similarity: '79%',
      description: 'Similar charges, defense emphasized procedural lapses in investigation. Bail granted with strict monitoring conditions.'
    }
  ];

  const handleQuickAction = (action) => {
    setIsSearching(true);
    
    setTimeout(() => {
      setIsSearching(false);
      
      if (action === 'explain') {
        setChatMessages([...chatMessages, 
          { type: 'user', content: 'Explain the key charges in the FIR' },
          { 
            type: 'assistant', 
            content: `Based on the FIR, the key charges are:

**IPC Section 306, 304(ii), 323, 504**

1. **Section 306** - Abetment of suicide: The FIR alleges the applicants created circumstances that led to mental distress.

2. **Section 304(ii)** - Culpable homicide not amounting to murder: Suggests knowledge that actions might cause death but without intention.

3. **Section 323** - Voluntarily causing hurt: Physical assault allegations supported by medical examination.

4. **Section 504** - Intentional insult with intent to provoke breach of peace.

The charges suggest a bail application context where the defense should focus on lack of direct intention, procedural compliance, and mitigating circumstances.`
          }
        ]);
      } else if (action === 'similar') {
        setChatMessages([...chatMessages,
          { type: 'user', content: 'Find similar cases based on these facts' },
          { 
            type: 'assistant', 
            content: 'I found 3 similar cases. You can review them below and add relevant ones to your dossier for detailed analysis.',
            cases: similarCases
          }
        ]);
      } else if (action === 'defense') {
        setChatMessages([...chatMessages,
          { type: 'user', content: 'Suggest a defense strategy for this bail application' },
          { 
            type: 'assistant', 
            content: `**Recommended Defense Strategy:**

**Primary Arguments:**

1. **Lack of Direct Intention** (Section 306, 304)
   - Emphasize absence of mens rea for abetment
   - Challenge causation link between alleged actions and outcome
   - Argue charges are disproportionate to facts

2. **Medical Evidence Analysis**
   - Review medical examination report for consistency
   - Highlight any gaps between medical findings and allegations
   - Question severity assessment

3. **Procedural Safeguards**
   - Ensure all procedural requirements were met during arrest
   - Check for compliance with arrest documentation
   - Verify witness statement procedures

4. **Bail Conditions**
   - Propose strong supervision conditions
   - Offer to surrender passport/travel documents
   - Suggest regular reporting to police station
   - Provide local surety with substantial assets

**Case Law Support:**
Reference similar cases like State vs Rajesh Sharma (2020) where bail was granted despite similar charges when defense successfully demonstrated lack of intention and proposed strict bail conditions.

**Risk Mitigation:**
Emphasize applicant's roots in community, no flight risk, and willingness to cooperate with investigation.`
          }
        ]);
      } else if (action === 'bail') {
        setChatMessages([...chatMessages,
          { type: 'user', content: 'Analyze the bail strategy' },
          { 
            type: 'assistant', 
            content: `**Bail Strategy Analysis:**

**Current Position:**
This is a regular bail application (Criminal Bail Application No. 2793 of 2021) in the Bombay High Court.

**Strategic Considerations:**

1. **Timing**: Application filed relatively early, which is favorable
2. **Court**: High Court jurisdiction provides better precedent application
3. **Charges**: Non-capital offenses, bail is generally not precluded

**Recommended Approach:**

✓ Emphasize liberty is the norm, jail is exception
✓ Highlight that charges are bailable under certain interpretations
✓ Argue no tampering risk - witnesses already examined
✓ Show strong community ties and employment
✓ Offer stringent bail conditions proactively

**Precedents to Cite:**
- *Sanjay Chandra vs CBI* (2012) - bail should be rule, jail exception
- *Arnesh Kumar vs State of Bihar* (2014) - unnecessary arrests to be avoided

**Conditions to Propose:**
- Personal bond of ₹50,000-1,00,000
- Two local sureties
- Bi-weekly reporting to investigating officer
- No contact with witnesses
- Surrender of passport`
          }
        ]);
      }
    }, 1500);
  };

  const addCaseToDossier = (caseItem) => {
    if (!savedCases.find(c => c.id === caseItem.id)) {
      setSavedCases([...savedCases, caseItem]);
      setChatMessages([...chatMessages, {
        type: 'system',
        content: `Added "${caseItem.name}" to your dossier. You can now ask questions about this case.`
      }]);
    }
  };

  const handleSavedCaseQuery = (caseName) => {
    setIsSearching(true);
    
    setTimeout(() => {
      setIsSearching(false);
      setChatMessages([...chatMessages,
        { type: 'user', content: `What was the defense strategy in ${caseName}?` },
        { 
          type: 'assistant', 
          content: `**Defense Strategy in ${caseName}:**

**Key Arguments Presented:**

1. **Absence of Mens Rea**
   - Defense successfully established lack of criminal intention
   - Argued that circumstances were misconstrued by prosecution
   - Presented alternative explanation for events

2. **Procedural Irregularities**
   - Highlighted delays in filing FIR (5 days)
   - Questioned chain of custody for evidence
   - Challenged credibility of witness statements due to inconsistencies

3. **Medical Evidence Reinterpretation**
   - Expert witness testimony contradicted prosecution's theory
   - Showed injuries were superficial and not life-threatening
   - Established that medical timeline didn't align with allegations

4. **Character Evidence**
   - Presented clean prior record
   - Multiple character witnesses from community
   - Employment verification and social standing

**Outcome:**
Court granted bail with conditions:
- Personal bond of ₹75,000
- Two sureties
- Weekly reporting
- No witness contact

**Key Takeaway:**
The success hinged on procedural challenges and credible alternative narrative rather than just arguing minor charges. The defense proactively offered strict bail conditions, which influenced the court favorably.`
        }
      ]);
    }, 1500);
  };

  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      {/* Left Panel - File Explorer */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <button className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-900 text-white rounded hover:bg-blue-800 transition-colors">
            <Plus size={18} />
            <span className="text-sm font-medium">Add Files/Folders</span>
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          <div className="mb-2">
            <div className="flex items-center gap-2 text-gray-700 mb-2">
              <Folder size={18} className="text-blue-900" />
              <span className="text-sm font-medium">Case_2793_Aakash_Tiwari_vs_State</span>
            </div>
            <div className="ml-6 space-y-1">
              {caseFiles.map((file) => (
                <div
                  key={file.name}
                  className="flex items-center gap-2 px-2 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded cursor-pointer"
                  onClick={() => setActiveTab(file.name)}
                >
                  <file.icon size={16} className="text-gray-500" />
                  <span className="truncate">{file.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Center Panel - Document Viewer */}
      <div className="flex-1 flex flex-col bg-gray-100">
        {/* Tabs */}
        <div className="bg-white border-b border-gray-200 flex items-center overflow-x-auto">
          {caseFiles.map((file) => (
            <div
              key={file.name}
              onClick={() => setActiveTab(file.name)}
              className={`flex items-center gap-2 px-4 py-2 border-r border-gray-200 cursor-pointer min-w-fit ${
                activeTab === file.name
                  ? 'bg-gray-100 text-blue-900 border-b-2 border-blue-900'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <FileText size={16} />
              <span className="text-sm font-medium truncate max-w-[150px]">{file.name}</span>
            </div>
          ))}
        </div>

        {/* Document Content */}
        <div className="flex-1 overflow-auto p-8">
          <div className="max-w-4xl mx-auto bg-white shadow-lg rounded-lg p-8">
            {activeTab === 'FIR_Copy.pdf' && (
              <div className="space-y-4">
                <div className="text-center mb-6">
                  <p className="text-xs text-gray-500 mb-2">33.2791.21 BA.doc</p>
                  <p className="text-xs text-gray-500 mb-4">DSM</p>
                  <h1 className="text-xl font-bold mb-4">IN THE HIGH COURT OF JUDICATURE AT BOMBAY<br/>CRIMINAL APPELLATE JURISDICTION</h1>
                  <p className="font-semibold">CRIMINAL BAIL APPLICATION NO. 2793 OF 2021</p>
                </div>
                
                <div className="space-y-2 text-sm">
                  <p>AAKASH S. TIWARI AND ANR ....APPLICANTS</p>
                  <p className="text-center">V/s</p>
                  <p>THE STATE OF MAHARASHTRA ....RESPONDENT</p>
                </div>

                <div className="my-6 text-center font-semibold text-sm">
                  <p>WITH</p>
                  <p>INTERIM APPLICATION NO. 2602 OF 2021</p>
                  <p>IN</p>
                  <p>CRIMINAL BAIL APPLICATION NO. 2793 OF 2021</p>
                </div>

                <div className="space-y-2 text-sm">
                  <p>ANIL KUMAR MISHRA ....APPLICANT</p>
                  <p className="font-semibold">IN THE MATTER BETWEEN</p>
                  <p>AAKASH S. TIWARI AND ANR ....APPLICANTS</p>
                  <p className="text-center">V/s</p>
                  <p>THE STATE OF MAHARASHTRA ....RESPONDENT</p>
                </div>

                <div className="mt-6 space-y-2 text-sm">
                  <p>Mr. Mukesh Mishra r/b Lawmatics India for the applicants</p>
                  <p>Mrs. J. S. Lohokare APP for the State</p>
                </div>

                <div className="my-6 text-center font-semibold">
                  <p>CORAM : NITIN W. SAMBRE, J.</p>
                  <p className="mt-2">DATE: DECEMBER 3, 2021.</p>
                </div>

                <div className="space-y-4 text-sm">
                  <p className="font-semibold">P.C.:</p>
                  <p>1) Applicant is seeking regular bail in C.R. No. 61/2021 registered with Nanghar Police Station for Offences punishable under Sections 306, 304(ii), 323, 504, 506 r/w 34 of the Indian Penal Code.</p>
                </div>

                <div className="text-center text-xs text-gray-500 mt-8">
                  <p>1/3</p>
                </div>
              </div>
            )}

            {activeTab === 'Medical_Examination_Report.pdf' && (
              <div className="space-y-4">
                <div className="text-center mb-6">
                  <h1 className="text-xl font-bold mb-4">MEDICAL EXAMINATION REPORT</h1>
                  <p className="text-sm">Government General Hospital, Nanghar</p>
                  <p className="text-xs text-gray-500">Case Ref: CR-61/2021</p>
                </div>
                
                <div className="space-y-3 text-sm">
                  <div className="grid grid-cols-2 gap-2">
                    <p><span className="font-semibold">Patient Name:</span> [Redacted]</p>
                    <p><span className="font-semibold">Age/Sex:</span> 34 Years / Male</p>
                    <p><span className="font-semibold">Date of Examination:</span> March 15, 2021</p>
                    <p><span className="font-semibold">Time:</span> 14:30 hours</p>
                  </div>

                  <div className="border-t pt-3 mt-4">
                    <p className="font-semibold mb-2">INJURIES NOTED:</p>
                    <ol className="list-decimal ml-6 space-y-2">
                      <li>Contusion on left shoulder - 3cm x 2cm, reddish-blue in color</li>
                      <li>Abrasion on right forearm - 2cm x 1cm, superficial</li>
                      <li>Tenderness over right chest wall, no visible injury</li>
                      <li>Minor laceration on left knee - 1.5cm, cleaned and dressed</li>
                    </ol>
                  </div>

                  <div className="border-t pt-3 mt-4">
                    <p className="font-semibold mb-2">OPINION:</p>
                    <p>Injuries are simple in nature and caused by blunt force. Compatible with alleged assault. No grievous injuries noted. Patient is conscious, oriented, and hemodynamically stable.</p>
                  </div>

                  <div className="border-t pt-3 mt-4">
                    <p className="font-semibold">Medical Officer:</p>
                    <p>Dr. Rajesh Kumar, MBBS, MD</p>
                    <p className="text-xs text-gray-500">Registration No: MH-45821</p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'Witness_Statements.pdf' && (
              <div className="space-y-4">
                <div className="text-center mb-6">
                  <h1 className="text-xl font-bold mb-4">WITNESS STATEMENTS</h1>
                  <p className="text-sm">C.R. No. 61/2021 - Nanghar Police Station</p>
                </div>
                
                <div className="space-y-6 text-sm">
                  <div className="border-b pb-4">
                    <p className="font-semibold text-base mb-2">WITNESS 1: Ramesh Patil</p>
                    <p className="mb-2"><span className="font-semibold">Relation to complainant:</span> Neighbor</p>
                    <p className="mb-2"><span className="font-semibold">Statement recorded on:</span> March 16, 2021</p>
                    <p className="italic">"I heard loud voices and sounds of argument from the adjacent house around 8:00 PM on March 14, 2021. I saw the accused persons leaving the premises in an agitated state around 8:30 PM. The victim appeared distressed when I met him the next morning."</p>
                  </div>

                  <div className="border-b pb-4">
                    <p className="font-semibold text-base mb-2">WITNESS 2: Priya Deshmukh</p>
                    <p className="mb-2"><span className="font-semibold">Relation to complainant:</span> Colleague</p>
                    <p className="mb-2"><span className="font-semibold">Statement recorded on:</span> March 17, 2021</p>
                    <p className="italic">"The victim had mentioned receiving threatening calls a week before the incident. He seemed worried and mentioned conflicts with the accused over property matters. On March 15, he came to office with visible injuries on his arm."</p>
                  </div>

                  <div className="pb-4">
                    <p className="font-semibold text-base mb-2">WITNESS 3: Inspector Suresh Yadav</p>
                    <p className="mb-2"><span className="font-semibold">Position:</span> Investigating Officer</p>
                    <p className="mb-2"><span className="font-semibold">Statement recorded on:</span> March 18, 2021</p>
                    <p className="italic">"Upon receiving the complaint, we immediately visited the scene. Evidence of disturbance was visible. Medical examination was conducted as per procedure. Accused were arrested on March 19, 2021, and statements recorded under Section 161 CrPC."</p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'Charge_Sheet.pdf' && (
              <div className="space-y-4">
                <div className="text-center mb-6">
                  <h1 className="text-xl font-bold mb-4">CHARGE SHEET</h1>
                  <p className="text-sm">C.R. No. 61/2021</p>
                  <p className="text-xs text-gray-500">Nanghar Police Station</p>
                </div>
                
                <div className="space-y-4 text-sm">
                  <div>
                    <p className="font-semibold mb-2">TO,</p>
                    <p>The Hon'ble Chief Judicial Magistrate</p>
                    <p>Nanghar District Court</p>
                  </div>

                  <div className="border-t pt-3 mt-4">
                    <p className="font-semibold mb-2">ACCUSED PERSONS:</p>
                    <ol className="list-decimal ml-6 space-y-1">
                      <li>Aakash S. Tiwari - Age 32, Resident of Nanghar</li>
                      <li>Anil Kumar Mishra - Age 35, Resident of Nanghar</li>
                    </ol>
                  </div>

                  <div className="border-t pt-3 mt-4">
                    <p className="font-semibold mb-2">SECTIONS INVOKED:</p>
                    <ul className="ml-6 space-y-2">
                      <li><span className="font-semibold">Section 306 IPC:</span> Abetment of suicide</li>
                      <li><span className="font-semibold">Section 304(ii) IPC:</span> Culpable homicide not amounting to murder</li>
                      <li><span className="font-semibold">Section 323 IPC:</span> Voluntarily causing hurt</li>
                      <li><span className="font-semibold">Section 504 IPC:</span> Intentional insult with intent to provoke breach of peace</li>
                      <li><span className="font-semibold">Section 506 IPC:</span> Criminal intimidation</li>
                      <li><span className="font-semibold">Section 34 IPC:</span> Acts done by several persons in furtherance of common intention</li>
                    </ul>
                  </div>

                  <div className="border-t pt-3 mt-4">
                    <p className="font-semibold mb-2">BRIEF FACTS:</p>
                    <p className="mb-2">The complainant alleged that the accused persons, due to a property dispute, committed assault on March 14, 2021, and issued threats causing mental distress. The incident resulted in physical injuries as documented in the medical examination report.</p>
                    <p>Investigation revealed evidence supporting the allegations. Witness statements corroborate the sequence of events. The accused were arrested on March 19, 2021.</p>
                  </div>

                  <div className="border-t pt-3 mt-4">
                    <p className="font-semibold">Investigating Officer:</p>
                    <p>Inspector Suresh Yadav</p>
                    <p className="text-xs text-gray-500">Badge No: 4521</p>
                    <p className="mt-2">Date: March 25, 2021</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right Panel - AI Assistant */}
      <div className="w-96 bg-white border-l border-gray-200 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 bg-blue-900">
          <div className="flex items-center gap-2">
            <Scale className="text-amber-500" size={24} />
            <h2 className="text-xl font-bold text-white">Casemind</h2>
          </div>
          <p className="text-xs text-blue-200 mt-1">Legal AI Assistant</p>
        </div>

        {/* Quick Actions */}
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <p className="text-xs font-semibold text-gray-600 mb-2">QUICK ACTIONS</p>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handleQuickAction('explain')}
              disabled={isSearching}
              className="flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded text-xs hover:border-blue-900 hover:text-blue-900 transition-colors disabled:opacity-50"
            >
              <BookOpen size={14} />
              <span>Explain document</span>
            </button>
            <button
              onClick={() => handleQuickAction('similar')}
              disabled={isSearching}
              className="flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded text-xs hover:border-blue-900 hover:text-blue-900 transition-colors disabled:opacity-50"
            >
              <Search size={14} />
              <span>Find similar cases</span>
            </button>
            <button
              onClick={() => handleQuickAction('defense')}
              disabled={isSearching}
              className="flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded text-xs hover:border-blue-900 hover:text-blue-900 transition-colors disabled:opacity-50"
            >
              <Shield size={14} />
              <span>Defense strategy</span>
            </button>
            <button
              onClick={() => handleQuickAction('bail')}
              disabled={isSearching}
              className="flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded text-xs hover:border-blue-900 hover:text-blue-900 transition-colors disabled:opacity-50"
            >
              <FileCheck size={14} />
              <span>Bail strategy</span>
            </button>
          </div>
        </div>

        {/* Saved Cases */}
        {savedCases.length > 0 && (
          <div className="p-4 border-b border-gray-200 bg-amber-50">
            <p className="text-xs font-semibold text-gray-600 mb-2">SAVED TO DOSSIER</p>
            <div className="space-y-2">
              {savedCases.map((caseItem) => (
                <div key={caseItem.id} className="bg-white p-2 rounded border border-amber-200">
                  <p className="text-xs font-medium text-gray-800">{caseItem.name}</p>
                  <button
                    onClick={() => handleSavedCaseQuery(caseItem.name)}
                    className="text-xs text-blue-900 hover:underline mt-1"
                  >
                    View defense strategy →
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {chatMessages.map((message, index) => (
            <div key={index}>
              {message.type === 'system' && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="text-sm text-blue-900">{message.content}</p>
                </div>
              )}
              
              {message.type === 'user' && (
                <div className="bg-gray-100 rounded-lg p-3 ml-8">
                  <p className="text-sm text-gray-800">{message.content}</p>
                </div>
              )}
              
              {message.type === 'assistant' && (
                <div className="bg-white border border-gray-200 rounded-lg p-3">
                  <p className="text-sm text-gray-800 whitespace-pre-line">{message.content}</p>
                  
                  {message.cases && (
                    <div className="mt-4 space-y-3">
                      {message.cases.map((caseItem) => (
                        <div key={caseItem.id} className="border border-gray-200 rounded p-3 hover:border-blue-900 transition-colors">
                          <div className="flex justify-between items-start mb-2">
                            <div>
                              <p className="text-sm font-semibold text-gray-800">{caseItem.name}</p>
                              <p className="text-xs text-gray-500">{caseItem.court} • {caseItem.year}</p>
                            </div>
                            <span className="text-xs font-semibold text-amber-600 bg-amber-50 px-2 py-1 rounded">
                              {caseItem.similarity}
                            </span>
                          </div>
                          <p className="text-xs text-gray-600 mb-2">{caseItem.description}</p>
                          <button
                            onClick={() => addCaseToDossier(caseItem)}
                            className="text-xs text-blue-900 hover:underline font-medium"
                          >
                            + Add to dossier
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          
          {isSearching && (
            <div className="flex items-center gap-2 text-blue-900">
              <Loader2 size={16} className="animate-spin" />
              <span className="text-sm">Analyzing...</span>
            </div>
          )}
        </div>

        {/* Chat Input */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask about the case..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-900"
            />
            <button className="px-4 py-2 bg-blue-900 text-white rounded hover:bg-blue-800 transition-colors">
              <Search size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CasemindDemo;