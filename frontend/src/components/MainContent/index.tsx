import React from 'react';
import CodeToolbar from './CodeToolbar';
import CodeEditor from './CodeEditor';

const MainContent: React.FC = () => {
  return (
    <div className="flex flex-col h-full bg-dark-darkest overflow-hidden min-w-0">
      <CodeToolbar />
      <CodeEditor />
    </div>
  );
};

export default MainContent;
