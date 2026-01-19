/**
 * Admin AI Test Spot
 * Internal testing playground (feature-flagged)
 * Uses centralized admin API client
 */
import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { 
  Bot, MessageSquare, Send, RefreshCw, AlertTriangle, 
  Sparkles, Terminal, FileText, ChevronRight, Trash2, AlertCircle
} from 'lucide-react';

// Centralized Admin API
import { settingsApi, auditApi, getErrorMessage } from '../../api/admin';

const AdminAITestSpot = () => {
  const [testInfo, setTestInfo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState('client_query');
  const [logs, setLogs] = useState([]);
  const [showLogs, setShowLogs] = useState(false);
  const [error, setError] = useState(null);

  const fetchTestInfo = useCallback(async () => {
    try {
      const response = await settingsApi.get();
      setTestInfo(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch test info:', err);
      setError(getErrorMessage(err, 'Failed to load test info'));
    }
  }, []);

  const fetchLogs = useCallback(async () => {
    try {
      const response = await auditApi.getLogs({ limit: 20 });
      setLogs(response.data.logs || []);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    }
  }, []);

  useEffect(() => {
    fetchTestInfo();
    fetchLogs();
  }, [fetchTestInfo, fetchLogs]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || loading) return;

    const userMessage = { role: 'user', content: inputMessage };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInputMessage('');
    setLoading(true);

    try {
      // AI test simulation - placeholder response
      // This endpoint may not exist in backend
      setMessages([...updatedMessages, {
        role: 'assistant',
        content: `[Test Mode] Received "${userMessage.content}" with scenario: ${selectedScenario}. This is a placeholder response. Backend AI integration is not implemented.`
      }]);
      toast.info('Test message processed (placeholder mode)');
      fetchLogs();
    } catch (err) {
      console.error('Failed to simulate:', err);
      setMessages([...updatedMessages, {
        role: 'assistant',
        content: 'Error: Failed to get response. Please try again.'
      }]);
      toast.error(getErrorMessage(err, 'Failed to process message'));
    } finally {
      setLoading(false);
    }
  };

  const handleSamplePrompt = (prompt) => {
    setInputMessage(prompt);
  };

  const clearMessages = () => {
    setMessages([]);
    toast.success('Chat cleared');
  };

  const scenarios = [
    { id: 'client_query', label: 'Client Query', description: 'Test client-facing responses' },
    { id: 'admin_action', label: 'Admin Action', description: 'Test admin command processing' },
    { id: 'telegram_command', label: 'Telegram Command', description: 'Test Telegram bot commands' }
  ];

  const samplePrompts = [
    'How do I make a deposit?',
    'What are my current bonuses?',
    'Process withdrawal for user123',
    'Show pending approvals'
  ];

  if (error && !testInfo) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={fetchTestInfo} 
            className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-lg text-white"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="ai-test-spot">
      {/* Warning Banner */}
      <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-6 h-6 text-yellow-400 flex-shrink-0" />
          <div>
            <h3 className="text-yellow-400 font-bold">Development Feature</h3>
            <p className="text-yellow-300/80 text-sm">
              This is an internal testing tool. Do not use in production with real data.
            </p>
          </div>
        </div>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Bot className="w-7 h-7 text-purple-400" />
            AI Test Spot
          </h1>
          <p className="text-gray-400 text-sm">Internal testing playground</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchLogs}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition"
            data-testid="refresh-logs-btn"
          >
            <RefreshCw className="w-5 h-5 text-gray-400" />
          </button>
          <button
            onClick={() => setShowLogs(!showLogs)}
            className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${
              showLogs ? 'bg-purple-500/20 text-purple-400' : 'bg-gray-800 text-gray-400'
            }`}
          >
            <Terminal className="w-4 h-4" />
            Logs
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat Panel */}
        <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden flex flex-col h-[600px]">
          {/* Scenario Selector */}
          <div className="px-4 py-3 border-b border-gray-800 bg-gray-800/50">
            <div className="flex gap-2">
              {scenarios.map(scenario => (
                <button
                  key={scenario.id}
                  onClick={() => setSelectedScenario(scenario.id)}
                  className={`px-3 py-1.5 rounded-lg text-sm transition ${
                    selectedScenario === scenario.id
                      ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                      : 'bg-gray-700 text-gray-400 border border-gray-600'
                  }`}
                >
                  {scenario.label}
                </button>
              ))}
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-500">
                <Sparkles className="w-12 h-12 mb-3" />
                <p>Start a conversation...</p>
                <p className="text-xs mt-2">Try a sample prompt below</p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[80%] rounded-xl px-4 py-2 ${
                    msg.role === 'user'
                      ? 'bg-purple-500/20 text-purple-100'
                      : 'bg-gray-800 text-gray-300'
                  }`}>
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-800 rounded-xl px-4 py-2">
                  <RefreshCw className="w-5 h-5 text-purple-400 animate-spin" />
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="p-4 border-t border-gray-800 bg-gray-800/50">
            {/* Sample Prompts */}
            <div className="flex flex-wrap gap-2 mb-3">
              {samplePrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSamplePrompt(prompt)}
                  className="px-3 py-1 bg-gray-700 text-gray-400 text-xs rounded-full hover:bg-gray-600 transition flex items-center gap-1"
                >
                  <ChevronRight className="w-3 h-3" />
                  {prompt}
                </button>
              ))}
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="Type a message..."
                className="flex-1 px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                disabled={loading}
                data-testid="chat-input"
              />
              <button
                onClick={clearMessages}
                className="p-2 bg-gray-700 hover:bg-gray-600 text-gray-400 rounded-lg transition"
                title="Clear chat"
              >
                <Trash2 className="w-5 h-5" />
              </button>
              <button
                onClick={sendMessage}
                disabled={loading || !inputMessage.trim()}
                className="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition disabled:opacity-50 flex items-center gap-2"
                data-testid="send-btn"
              >
                <Send className="w-4 h-4" />
                Send
              </button>
            </div>
          </div>
        </div>

        {/* Side Panel */}
        <div className="space-y-4">
          {/* Info Card */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="text-white font-medium mb-3 flex items-center gap-2">
              <FileText className="w-4 h-4 text-gray-400" />
              Test Configuration
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Scenario</span>
                <span className="text-white">{selectedScenario}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Messages</span>
                <span className="text-white">{messages.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Status</span>
                <span className="text-emerald-400">Ready</span>
              </div>
            </div>
          </div>

          {/* Logs Panel */}
          {showLogs && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 max-h-[400px] overflow-auto">
              <h3 className="text-white font-medium mb-3 flex items-center gap-2">
                <Terminal className="w-4 h-4 text-gray-400" />
                Recent Logs
              </h3>
              {logs.length === 0 ? (
                <p className="text-gray-500 text-sm">No logs available</p>
              ) : (
                <div className="space-y-2">
                  {logs.map((log, idx) => (
                    <div key={idx} className="p-2 bg-gray-800 rounded text-xs">
                      <div className="flex justify-between text-gray-500">
                        <span>{log.action}</span>
                        <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                      </div>
                      <p className="text-gray-300 mt-1">{log.details || 'No details'}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminAITestSpot;
