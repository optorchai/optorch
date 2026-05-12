/**
 * Authorization Approval Extension
 * 
 * Renders interactive authorization approval form when permission denied.
 * Handles interaction.request events from authorization adapter.
 */

const submittedInteractions = new Map();

export default {
  id: 'authorization-approval',
  name: 'Authorization Approval Extension',
  placement: 'pre',
  
  canHandle: (event) => {
    return event.event === 'interaction.request' && event.adapter === 'authorization';
  },
  
  renderContent: (event, context) => {
    const AuthorizationApprovalForm = () => {
      const { form, interaction_id } = event;
      const submission = submittedInteractions.get(interaction_id);
      
      if (!form) {
        return (
          <div className="inline-block mt-4 p-4 border rounded-lg shadow-md" style={{ borderColor: 'hsl(0 84.2% 60.2% / 0.3)', backgroundColor: 'hsl(0 84.2% 60.2% / 0.1)' }}>
            <p className="text-sm" style={{ color: 'hsl(0 84.2% 60.2%)' }}>❌ Invalid authorization approval event - missing form data</p>
          </div>
        );
      }

      const formData = form.data || {};
      const uiSchema = form.uiSchema || {};
      
      const [approved, setApproved] = window.React.useState(formData.approved || false);
      const [justification, setJustification] = window.React.useState(formData.justification || '');
      const [duration, setDuration] = window.React.useState(formData.duration || 3600);

      // readonly fields to display
      const readonlyFields = Object.entries(uiSchema)
        .filter(([_, config]) => config.widget === 'readonly')
        .map(([fieldName, config]) => ({
          name: fieldName,
          label: config.label || fieldName,
          value: formData[fieldName],
          highlight: config.highlight,
        }));
      
      const handleSubmit = async () => {
        if (!justification.trim()) {
          alert('Justification required');
          return;
        }

        const response = {
          interaction_id,
          data: {
            approved: true, 
            justification: justification.trim(),
            duration: parseInt(duration, 10)
          }
        };

        submittedInteractions.set(interaction_id, { approved: true, justification, duration });
        
        try {
          await fetch(`${context.apiBaseUrl || ''}/interact`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(response)
          });
        } catch (error) {
          console.error('Failed to submit authorization approval:', error);
          submittedInteractions.delete(interaction_id);
        }
      };
      
      const handleDeny = async () => {
        const response = {
          interaction_id,
          data: {
            approved: false,
            justification: justification.trim() || 'access denied'
          }
        };
        
        submittedInteractions.set(interaction_id, { approved: false, justification });
        
        try {
          await fetch(`${context.apiBaseUrl || ''}/interact`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(response)
          });
        } catch (error) {
          console.error('Failed to deny authorization:', error);
          submittedInteractions.delete(interaction_id);
        }
      };

      // risk level colors
      const riskColor = {
        low: 'hsl(142 76% 36%)',
        medium: 'hsl(38 92% 50%)',
        high: 'hsl(25 95% 53%)',
        critical: 'hsl(0 84.2% 60.2%)'
      }[formData.risk_level] || 'hsl(38 92% 50%)';
      
      return (
        <div className="inline-block mt-4 p-4 border rounded-lg shadow-md" style={{ borderColor: `${riskColor} / 0.3`, backgroundColor: `${riskColor} / 0.1` }}>
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🔒</span>
              <h4 className="font-semibold text-base" style={{ color: riskColor }}>Authorization Required</h4>
            </div>
            
            <div className="grid grid-cols-2 gap-3 text-xs mb-4">
              {readonlyFields.map(field => (
                <div key={field.name}>
                  <span className="opacity-60">{field.label}:</span>
                  <span 
                    className="ml-2 font-medium" 
                    style={{ color: field.highlight ? riskColor : undefined }}
                  >
                    {field.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
          
          {!submission && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium mb-1">
                  Justification <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  placeholder="Why do you need access to this resource?"
                  className="w-full px-3 py-2 text-sm border rounded resize-none"
                  rows="3"
                />
              </div>

              {uiSchema.duration && (
                <div>
                  <label className="block text-xs font-medium mb-1">
                    Access Duration (seconds)
                  </label>
                  <input
                    type="number"
                    value={duration}
                    onChange={(e) => setDuration(e.target.value)}
                    min="60"
                    max="86400"
                    className="w-full px-3 py-2 text-sm border rounded"
                  />
                  <p className="text-xs opacity-60 mt-1">
                    {duration >= 3600 ? `${(duration / 3600).toFixed(1)} hours` : `${duration} seconds`}
                  </p>
                </div>
              )}

              <div className="flex gap-2">
                <button
                  onClick={handleSubmit}
                  className="flex-1 px-4 py-2 text-sm font-medium text-white rounded transition-colors"
                  style={{ backgroundColor: riskColor }}
                >
                  Request Approval
                </button>
                <button
                  onClick={handleDeny}
                  className="px-4 py-2 text-sm font-medium border rounded transition-colors hover:bg-gray-100"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {submission && (
            <div className="text-sm">
              {submission.approved ? (
                <div className="flex items-center gap-2" style={{ color: riskColor }}>
                  <span>⏳</span>
                  <span>Approval requested - awaiting authorization...</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 opacity-60">
                  <span>✖️</span>
                  <span>Access request cancelled</span>
                </div>
              )}
            </div>
          )}
        </div>
      );
    };
    
    return <AuthorizationApprovalForm />;
  }
};
