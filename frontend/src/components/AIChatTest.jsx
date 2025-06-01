import React, { useState } from 'react';
import AIChatModal from './AIChatModal';

// Simple test component to verify AI Chat Modal functionality
const AIChatTest = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ padding: '2rem' }}>
      <h2>AI Chat Modal Test</h2>
      <p>This is a test component to verify the AI Chat Modal works correctly.</p>
      
      <button
        onClick={() => setIsOpen(true)}
        style={{
          backgroundColor: '#9b59b6',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          padding: '1rem 2rem',
          fontSize: '1rem',
          cursor: 'pointer'
        }}
      >
        Open AI Chat Modal
      </button>

      <AIChatModal 
        isOpen={isOpen} 
        onClose={() => setIsOpen(false)} 
      />
    </div>
  );
};

export default AIChatTest;
