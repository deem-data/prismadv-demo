import React, { useCallback, useEffect, useRef } from 'react';
import {
  Panel,
  Group as PanelGroup,
  Separator as PanelResizeHandle
} from 'react-resizable-panels';
import { useAppStore } from '@/store';
import Header from './Header';
import LeftSidebar from './LeftSidebar';
import MainContent from './MainContent';
import BottomPanel from './BottomPanel';
import RightSidebar from './RightSidebar';
import LoadingOverlay from './LoadingOverlay';
import GenerationProgressBar from './GenerationProgressBar';
import ToastContainer from './Toast';
import { WelcomeScreen } from './WelcomeScreen';

const AppLayout: React.FC = () => {
  const { ui, taskFile } = useAppStore();
  const resizeRafRef = useRef<number | null>(null);

  const dispatchWindowResize = useCallback(() => {
    if (resizeRafRef.current !== null) return;

    resizeRafRef.current = window.requestAnimationFrame(() => {
      resizeRafRef.current = null;
      window.dispatchEvent(new Event('resize'));
    });
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (ui.themePreference === 'system') {
      root.removeAttribute('data-theme');
    } else {
      root.setAttribute('data-theme', ui.themePreference);
    }
  }, [ui.themePreference]);

  useEffect(() => {
    return () => {
      if (resizeRafRef.current !== null) {
        window.cancelAnimationFrame(resizeRafRef.current);
        resizeRafRef.current = null;
      }
    };
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen bg-dark-darkest text-text-primary overflow-hidden">
      <Header />

      {!taskFile ? (
        <div className="flex-1 overflow-hidden">
          <WelcomeScreen />
        </div>
      ) : (
      <div className="flex-1 flex overflow-hidden">
        <PanelGroup
          orientation="horizontal"
          className="h-full w-full"
          id="prismadv-layout-v5-fixed"
          onLayoutChange={dispatchWindowResize}
        >
          {/* Left Sidebar */}
          {!ui.leftSidebarCollapsed && (
            <>
              <Panel 
                defaultSize="20%" 
                minSize="10%" 
                maxSize="40%"
                collapsible={false}
                className="h-full"
              >
                <div className="flex flex-col h-full w-full overflow-hidden">
                  <LeftSidebar />
                </div>
              </Panel>
              <PanelResizeHandle className="relative w-2 bg-dark-darkest hover:bg-accent-textual transition-colors cursor-col-resize flex items-center justify-center z-50">
                <div className="w-0.5 h-8 bg-dark-border rounded-full" />
              </PanelResizeHandle>
            </>
          )}

          {/* Main Area (Code + Bottom Panel) */}
          <Panel className="h-full" minSize="30%">
            <div className="flex flex-col h-full w-full overflow-hidden">
              <PanelGroup
                orientation="vertical"
                className="h-full w-full"
                onLayoutChange={dispatchWindowResize}
              >
                <Panel className="h-full" minSize="30%">
                  <div className="flex flex-col h-full w-full overflow-hidden">
                    <MainContent />
                  </div>
                </Panel>
                
                {!ui.bottomPanelCollapsed && (
                  <>
                    <PanelResizeHandle className="relative h-2 bg-dark-darkest hover:bg-accent-textual transition-colors cursor-row-resize flex items-center justify-center z-50">
                      <div className="h-0.5 w-8 bg-dark-border rounded-full" />
                    </PanelResizeHandle>
                    <Panel 
                      defaultSize="40%" 
                      minSize="15%" 
                      className="bg-dark-medium border-t border-dark-darkest h-full"
                    >
                      <div className="flex flex-col h-full w-full overflow-hidden">
                        <BottomPanel />
                      </div>
                    </Panel>
                  </>
                )}
              </PanelGroup>
            </div>
          </Panel>

          {/* Right Sidebar */}
          {!ui.rightSidebarCollapsed && (
            <>
              <PanelResizeHandle className="relative w-2 bg-dark-darkest hover:bg-accent-textual transition-colors cursor-col-resize flex items-center justify-center z-50">
                <div className="w-0.5 h-8 bg-dark-border rounded-full" />
              </PanelResizeHandle>
              <Panel 
                defaultSize="25%" 
                minSize="160px"
                maxSize="40%"
                collapsible={false}
                className="bg-dark-medium border-l border-dark-darkest h-full"
              >
                <div className="flex flex-col h-full w-full overflow-hidden">
                  <RightSidebar />
                </div>
              </Panel>
            </>
          )}
        </PanelGroup>
      </div>
      )}

      <GenerationProgressBar />
      <LoadingOverlay />
      <ToastContainer />
    </div>
  );
};

export default AppLayout;
