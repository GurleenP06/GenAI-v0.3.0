const API_BASE = 'http://127.0.0.1:8000';

const SECTION_CONFIG = {
  rlpm: {
    assistants: [
      { type: 'rlpm', label: 'RLPM Analyst' },
      { type: 'opo', label: 'OPO Search' },
      { type: 'writing', label: 'Writing' },
      { type: 'document', label: 'Document' }
    ],
    defaultAssistant: 'rlpm',
    welcomeTitle: 'OSKAR - RLPM Assistant',
    welcomeDescription: 'Analyze procedures for RLPM compliance, search OPO documents, or get writing help',
    prompts: [
      { label: 'RLPM Check', text: 'Check procedure for RLPM compliance', prompt: 'Check OPMP 3.05 for RLPM compliance' },
      { label: 'RLPM Changes', text: 'What changes are needed for RLPM?', prompt: 'What RLPM changes are needed for IMP' },
      { label: 'RLPM Stages', text: 'RLPM stages and gates', prompt: 'Explain the RLPM stages and gate requirements from GCP-59' },
      { label: 'Compare', text: 'Compare Old vs New procedures', prompt: 'Show the comparison results for Old vs New IMP 07-01-01' },
      { label: 'OPO Search', text: 'Search OPO documents', prompt: 'Find OPMP procedures for' },
      { label: 'General', text: 'Ask anything', prompt: 'Help me with' }
    ]
  },
  standard: {
    assistants: [
      { type: 'opo', label: 'OPO Search' },
      { type: 'writing', label: 'Writing' },
      { type: 'document', label: 'Document' }
    ],
    defaultAssistant: 'opo',
    welcomeTitle: 'OSKAR',
    welcomeDescription: 'Operations Support Knowledge Assistant with RAG - Select a prompt below or type your own question',
    prompts: [
      { label: 'Inventory', text: 'Blind inventory and cycle counting', prompt: 'Explain blind inventory procedures' },
      { label: 'AS9100D', text: 'Quality standards', prompt: 'AS9100D requirements for' },
      { label: 'OPMP', text: 'Operations procedures', prompt: 'Find OPMP procedures for' },
      { label: 'IMP', text: 'Industrial procedures', prompt: 'Search IMP documents about' },
      { label: 'Audit', text: 'Audit requirements', prompt: 'Audit checklist for' },
      { label: 'General', text: 'Ask anything', prompt: 'Help me with' }
    ]
  }
};
