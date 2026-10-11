
class VoiceAgentStudio {
  constructor() {
    this.inCall = false;
    this.callSeconds = 0;
    this.callTimerInterval = null;
    this.synth = window.speechSynthesis || null;
    this.recognition = null;
    this.isListening = false;
    this.currentState = null;
    this.conversationTranscript = [];

    this.initElements();
    this.initSpeechRecognition();
    this.initEventListeners();
    this.fetchInitialState();
    this.fetchPromptPreview();
    this.loadScenariosList();
  }

  initElements() {
    this.globalStatusText = document.getElementById('global-status-text');
    this.globalChecklistCount = document.getElementById('global-checklist-count');
    this.callLiveDot = document.getElementById('call-live-dot');
    this.quickResetBtn = document.getElementById('quick-reset-btn');

    this.agentDisplayName = document.getElementById('agent-display-name');
    this.customerTargetDisplay = document.getElementById('customer-target-display');
    this.agentInitialsDisplay = document.getElementById('agent-initials-display');
    this.avatarPulseRing = document.getElementById('avatar-pulse-ring');
    this.callClockDisplay = document.getElementById('call-clock-display');
    this.waveVisualizer = document.getElementById('wave-visualizer');
    this.voiceStatusLabel = document.getElementById('voice-status-label');
    this.dialogueMessagesScroll = document.getElementById('dialogue-messages-scroll');
    this.clearFeedBtn = document.getElementById('clear-feed-btn');

    this.btnStartCall = document.getElementById('btn-start-call');
    this.btnMicToggle = document.getElementById('btn-mic-toggle');
    this.micBtnText = document.getElementById('mic-btn-text');
    this.btnEndCall = document.getElementById('btn-end-call');
    this.chatInputForm = document.getElementById('chat-input-form');
    this.chatInputField = document.getElementById('chat-input-field');
    this.btnSendMessage = document.getElementById('btn-send-message');
    this.suggestionChips = document.querySelectorAll('.suggestion-chip');

    this.opsTabBtns = document.querySelectorAll('.ops-tab-btn');
    this.opsTabPanes = document.querySelectorAll('.ops-tab-pane');

    this.decisionHeroCard = document.getElementById('decision-hero-card');
    this.decisionHeroIcon = document.getElementById('decision-hero-icon');
    this.decisionHeroTitle = document.getElementById('decision-hero-title');
    this.decisionHeroDesc = document.getElementById('decision-hero-desc');

    this.btnRunAllScenarios = document.getElementById('btn-run-all-scenarios');
    this.scenariosListContainer = document.getElementById('scenarios-list-container');
    this.studioConfigForm = document.getElementById('studio-config-form');
    this.studioPromptPreview = document.getElementById('studio-prompt-preview');
    this.btnExportRetell = document.getElementById('btn-export-retell');
    this.btnExportBolna = document.getElementById('btn-export-bolna');
    this.btnExportPrompt = document.getElementById('btn-export-prompt');
    this.languageSelect = document.getElementById('studio-cfg-language');
    this.agentGenderSelect = document.getElementById('studio-cfg-agent-gender');
    this.conversationLanguageSelect = document.getElementById('conversation-language-select');
    this.languageSaveStatus = document.getElementById('language-save-status');
    const savedLanguage = window.localStorage.getItem('home-credit-agent-language');
    this.currentLanguage = savedLanguage === 'English' ? 'English' : 'Hindi';
    this.conversationLanguageSelect.value = this.currentLanguage;
    this.languageSelect.value = this.currentLanguage;
    this.languageUpdatePromise = Promise.resolve();
    this.nameGate = document.getElementById('name-gate-overlay');
    this.customerNameForm = document.getElementById('customer-name-form');
    this.customerNameInput = document.getElementById('customer-name-input');
    this.customerNameError = document.getElementById('customer-name-error');
    this.customerNameSubmit = document.getElementById('customer-name-submit');

    const savedCustomerName = window.localStorage.getItem('home-credit-customer-name');
    if (savedCustomerName && savedCustomerName.trim()) {
      if (this.nameGate) {
        this.nameGate.hidden = true;
        this.nameGate.style.display = 'none';
      }
      const trimmedName = savedCustomerName.trim();
      if (this.customerNameInput) this.customerNameInput.value = trimmedName;
      const studioCustomerInput = document.getElementById('studio-cfg-customer');
      if (studioCustomerInput) studioCustomerInput.value = trimmedName;
      if (this.customerTargetDisplay) {
        this.customerTargetDisplay.innerHTML = `Calling: <strong>${trimmedName}</strong> • LAP Offer (₹75L)`;
      }
      fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_name: trimmedName })
      }).catch(err => console.warn('Failed to sync saved customer name:', err));
    }

    this.studioTelemetryJson = document.getElementById('studio-telemetry-json');
    this.btnTelemetryJson = document.getElementById('btn-telemetry-json');
    this.btnTelemetryTxt = document.getElementById('btn-telemetry-txt');
  }

  initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.lang = this.currentLanguage === 'Hindi' ? 'hi-IN' : 'en-IN';

      this.recognition.onstart = () => {
        this.isListening = true;
        this.btnMicToggle.classList.add('recording');
        this.micBtnText.textContent = 'Listening...';
        this.voiceStatusLabel.textContent = 'Listening to customer...';
        this.waveVisualizer.classList.add('animating');
      };

      this.recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          this.chatInputField.value = transcript;
          this.handleSendCustomerMessage(transcript);
        }
      };

      this.recognition.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        this.stopSpeechRecognition();
      };

      this.recognition.onend = () => {
        this.stopSpeechRecognition();
      };
    } else {
      console.warn('Web Speech API is not supported in this browser.');
    }
  }

  stopSpeechRecognition() {
    this.isListening = false;
    this.btnMicToggle.classList.remove('recording');
    this.micBtnText.textContent = 'Microphone (STT)';
    if (!this.synth || !this.synth.speaking) {
      this.waveVisualizer.classList.remove('animating');
      this.voiceStatusLabel.textContent = this.inCall ? 'In Call • Live' : 'Voice Agent Standby';
    }
  }

  initEventListeners() {
    this.customerNameForm.addEventListener('submit', (event) => {
      event.preventDefault();
      this.continueWithCustomerName();
    });

    this.btnStartCall.addEventListener('click', () => this.startCall());
    this.btnEndCall.addEventListener('click', () => this.endCall());
    this.clearFeedBtn.addEventListener('click', () => this.clearDialogueFeed());
    this.quickResetBtn.addEventListener('click', () => this.resetSession());

    this.btnMicToggle.addEventListener('click', () => {
      if (!this.recognition) {
        alert('Web Speech recognition is not available in your browser. Please type responses in the input box.');
        return;
      }
      if (this.isListening) {
        this.recognition.stop();
      } else {
        this.recognition.start();
      }
    });

    this.chatInputForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = this.chatInputField.value.trim();
      if (text) {
        this.chatInputField.value = '';
        this.handleSendCustomerMessage(text);
      }
    });

    this.suggestionChips.forEach(chip => {
      chip.addEventListener('click', () => {
        const languageKey = this.currentLanguage === 'Hindi' ? 'hi' : 'en';
        const text = chip.getAttribute(`data-text-${languageKey}`) || chip.getAttribute('data-text');
        if (text) {
          this.handleSendCustomerMessage(text);
        }
      });
    });

    const chipsScroll = document.getElementById('chips-scroll');
    if (chipsScroll) {
      chipsScroll.addEventListener('wheel', (e) => {
        if (e.deltaY !== 0) {
          e.preventDefault();
          chipsScroll.scrollLeft += e.deltaY;
        }
      }, { passive: false });
    }

    this.applyConversationLanguageUI();
    this.conversationLanguageSelect.addEventListener('change', () => {
      this.saveConversationLanguage().catch(() => {});
    });

    this.opsTabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const tabId = btn.getAttribute('data-tab');
        this.opsTabBtns.forEach(b => b.classList.remove('active'));
        this.opsTabPanes.forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(tabId).classList.add('active');
      });
    });

    this.studioConfigForm.addEventListener('submit', (e) => {
      e.preventDefault();
      this.applyStudioConfig();
    });

    this.btnExportRetell.addEventListener('click', () => this.copyRetellConfig());
    this.btnExportBolna.addEventListener('click', () => this.copyBolnaConfig());
    this.btnExportPrompt.addEventListener('click', () => this.copyPromptText());
    this.btnRunAllScenarios.addEventListener('click', () => this.runAllScenariosBatch());
    this.btnTelemetryJson.addEventListener('click', () => this.downloadTelemetryJSON());
    this.btnTelemetryTxt.addEventListener('click', () => this.downloadTranscriptTXT());
  }

  async fetchInitialState() {
    try {
      const res = await fetch('/api/state');
      const data = await res.json();
      this.currentState = data.state;
      this.renderStateMatrix(data.state);
      this.updateTelemetryViewer();
    } catch (err) {
      console.error('Initial state fetch error:', err);
    }
  }

  async fetchPromptPreview() {
    try {
      const res = await fetch('/api/prompt');
      const data = await res.json();
      this.studioPromptPreview.textContent = data.rendered_prompt;
    } catch (err) {
      console.error('Prompt fetch error:', err);
    }
  }

  getCustomerName() {
    const fromStorage = window.localStorage.getItem('home-credit-customer-name');
    if (fromStorage && fromStorage.trim()) return fromStorage.trim();
    if (this.customerNameInput && this.customerNameInput.value.trim()) return this.customerNameInput.value.trim();
    const studioInput = document.getElementById('studio-cfg-customer');
    if (studioInput && studioInput.value.trim()) return studioInput.value.trim();
    return '';
  }

  async startCall() {
    try {
      await this.saveConversationLanguage();
    } catch (err) {
      this.appendMessage('system', this.currentLanguage === 'Hindi'
        ? 'भाषा सेट नहीं हो सकी। कृपया सर्वर से कनेक्शन जाँचकर फिर कोशिश करें।'
        : 'Could not set the conversation language. Check the server connection and try again.');
      return;
    }

    this.inCall = true;
    this.callSeconds = 0;
    this.conversationTranscript = [];
    this.dialogueMessagesScroll.innerHTML = '';

    this.btnStartCall.disabled = true;
    this.btnEndCall.disabled = false;
    this.btnMicToggle.disabled = false;
    this.btnSendMessage.disabled = false;
    this.chatInputField.disabled = false;
    
    this.avatarPulseRing.classList.add('active');
    this.callLiveDot.classList.add('active');
    this.globalStatusText.textContent = 'CALL IN PROGRESS';
    this.voiceStatusLabel.textContent = 'Connecting outbound call...';

    clearInterval(this.callTimerInterval);
    this.callTimerInterval = setInterval(() => {
      this.callSeconds++;
      const mins = String(Math.floor(this.callSeconds / 60)).padStart(2, '0');
      const secs = String(this.callSeconds % 60).padStart(2, '0');
      this.callClockDisplay.textContent = `${mins}:${secs}`;
    }, 1000);

    try {
      const customerName = this.getCustomerName();
      const res = await fetch('/api/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: customerName || undefined,
          language_to_speak: this.currentLanguage
        })
      });
      const data = await res.json();
      this.handleAgentTurn(data.agent_reply, data.state);
    } catch (err) {
      console.error('Call start error:', err);
      this.appendMessage('system', 'Connection error reaching backend.');
    }
  }

  saveConversationLanguage() {
    const language = this.conversationLanguageSelect.value === 'English' ? 'English' : 'Hindi';
    this.currentLanguage = language;
    window.localStorage.setItem('home-credit-agent-language', language);
    this.applyConversationLanguageUI();

    const update = this.languageUpdatePromise.catch(() => {}).then(async () => {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language_to_speak: language })
      });
      if (!response.ok) throw new Error('Unable to update conversation language');
      const data = await response.json();
      if (data.config?.language_to_speak !== language) {
        throw new Error('Server language does not match the selected language');
      }
      this.studioPromptPreview.textContent = data.rendered_prompt;
      return data;
    });

    this.languageUpdatePromise = update;
    update.then(() => {
      if (this.languageSaveStatus && this.currentLanguage === language) {
        this.languageSaveStatus.textContent = language === 'Hindi'
          ? 'एजेंट हिंदी में बात करेगा'
          : 'Agent will speak in English';
      }
    }).catch(err => {
      if (this.languageSaveStatus && this.currentLanguage === language) {
        this.languageSaveStatus.textContent = language === 'Hindi'
          ? 'भाषा सहेजी नहीं जा सकी'
          : 'Could not save language';
      }
      console.error('Language update error:', err);
    });
    return update;
  }

  applyConversationLanguageUI() {
    const language = this.conversationLanguageSelect.value === 'English' ? 'English' : 'Hindi';
    const languageKey = language === 'Hindi' ? 'hi' : 'en';
    this.currentLanguage = language;
    this.languageSelect.value = language;

    if (this.recognition) {
      this.recognition.lang = language === 'Hindi' ? 'hi-IN' : 'en-IN';
    }

    this.suggestionChips.forEach(chip => {
      const label = chip.getAttribute(`data-label-${languageKey}`);
      const textSpan = chip.querySelector('.chip-text');
      if (textSpan && label) {
        textSpan.textContent = label;
      } else if (label) {
        chip.textContent = label;
      }
    });

    if (this.languageSaveStatus) {
      this.languageSaveStatus.textContent = language === 'Hindi'
        ? 'एजेंट हिंदी में बात करेगा'
        : 'Agent will speak in English';
    }
  }

  endCall() {
    this.inCall = false;
    clearInterval(this.callTimerInterval);
    if (this.synth) this.synth.cancel();
    if (this.isListening && this.recognition) this.recognition.stop();

    this.btnStartCall.disabled = false;
    this.btnEndCall.disabled = true;
    this.btnMicToggle.disabled = true;
    this.btnSendMessage.disabled = true;

    this.avatarPulseRing.classList.remove('active', 'speaking');
    this.waveVisualizer.classList.remove('animating');
    this.callLiveDot.classList.remove('active');
    this.globalStatusText.textContent = 'CALL ENDED';
    this.voiceStatusLabel.textContent = 'Call Concluded';

    this.appendMessage('system', 'Outbound call session closed.');
  }

  clearDialogueFeed() {
    this.dialogueMessagesScroll.innerHTML = '';
    this.conversationTranscript = [];
    this.appendMessage('system', 'Dialogue log cleared. Click "Start Call" to initiate conversation.');
  }

  async resetSession() {
    try {
      await fetch('/api/session/reset', { method: 'POST' });
      this.endCall();
      this.clearDialogueFeed();
      this.fetchInitialState();
      alert('Session and qualification state reset successfully.');
    } catch (err) {
      console.error('Reset error:', err);
    }
  }

  async handleSendCustomerMessage(text) {
    if (!this.inCall) {
      await this.startCall();
    }

    try {
      await this.languageUpdatePromise;
    } catch (err) {
      this.appendMessage('system', this.currentLanguage === 'Hindi'
        ? 'भाषा सेट नहीं हो सकी। कृपया सर्वर से कनेक्शन जाँचकर फिर कोशिश करें।'
        : 'Could not set the conversation language. Check the server connection and try again.');
      return;
    }

    this.appendMessage('customer', text);

    try {
      const customerName = this.getCustomerName();
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          customer_name: customerName || undefined,
          language_to_speak: this.currentLanguage
        })
      });
      const data = await res.json();
      this.handleAgentTurn(data.agent_reply, data.state);
    } catch (err) {
      console.error('Turn error:', err);
      this.appendMessage('system', 'Error sending utterance to agent.');
    }
  }

  handleAgentTurn(reply, state) {
    this.currentState = state;
    this.appendMessage('agent', reply);
    this.renderStateMatrix(state);
    this.updateTelemetryViewer();
    this.synthesizeSpeech(reply);

    if (['DISQUALIFIED', 'TRANSFERRED_SPECIALIST', 'BUSY_CALLBACK', 'QUALIFIED_HANDOFF', 'CALL_ENDED'].includes(state.current_stage)) {
      setTimeout(() => {
        if (this.inCall) {
          this.inCall = false;
          clearInterval(this.callTimerInterval);
          this.btnStartCall.disabled = false;
          this.btnEndCall.disabled = true;
          this.btnMicToggle.disabled = true;
          this.btnSendMessage.disabled = true;
          this.avatarPulseRing.classList.remove('active');
          this.voiceStatusLabel.textContent = `Call Concluded (${state.current_stage})`;
        }
      }, 3500);
    }
  }

  appendMessage(speaker, text) {
    const bubble = document.createElement('div');
    bubble.className = `dialogue-bubble ${speaker}`;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    if (speaker === 'agent') {
      const agentName = this.agentDisplayName.textContent.split(' ')[0] || 'Aisha';
      this.appendBubbleMeta(bubble, `AI Agent (${agentName})`, timeStr);
      this.appendBubbleText(bubble, text);
    } else if (speaker === 'customer') {
      this.appendBubbleMeta(bubble, 'Customer', timeStr);
      this.appendBubbleText(bubble, text);
    } else {
      this.appendBubbleText(bubble, text);
    }

    this.dialogueMessagesScroll.appendChild(bubble);
    this.dialogueMessagesScroll.scrollTop = this.dialogueMessagesScroll.scrollHeight;

    this.conversationTranscript.push({
      time: timeStr,
      speaker: speaker,
      text: text
    });
  }

  appendBubbleMeta(bubble, speakerLabel, timeLabel) {
    const meta = document.createElement('div');
    meta.className = 'bubble-meta';
    const speaker = document.createElement('span');
    speaker.textContent = speakerLabel;
    const time = document.createElement('span');
    time.textContent = timeLabel;
    meta.append(speaker, time);
    bubble.appendChild(meta);
  }

  appendBubbleText(bubble, text) {
    const paragraph = document.createElement('p');
    paragraph.textContent = text;
    bubble.appendChild(paragraph);
  }

  synthesizeSpeech(text) {
    if (!this.synth) return;
    this.synth.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    const languagePrefix = this.currentLanguage === 'Hindi' ? 'hi' : 'en';
    const isMaleAgent = this.agentGenderSelect?.value === 'Male';
    utterance.lang = this.currentLanguage === 'Hindi' ? 'hi-IN' : 'en-IN';
    utterance.rate = 1.0;
    utterance.pitch = isMaleAgent ? 0.96 : 1.04;

    const voices = this.synth.getVoices();
    const genderPattern = isMaleAgent ? /male|man/i : /female|woman/i;
    const preferredVoice = voices.find(v => v.lang.toLowerCase().startsWith(languagePrefix) && genderPattern.test(v.name))
      || voices.find(v => v.lang.toLowerCase().startsWith(languagePrefix) && (v.name.includes('Google') || v.name.includes('Natural')))
      || voices.find(v => v.lang.toLowerCase().startsWith(languagePrefix));
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.onstart = () => {
      this.avatarPulseRing.classList.add('speaking');
      this.waveVisualizer.classList.add('animating');
      this.voiceStatusLabel.textContent = 'Voice Agent Speaking...';
    };

    utterance.onend = () => {
      this.avatarPulseRing.classList.remove('speaking');
      if (!this.isListening) {
        this.waveVisualizer.classList.remove('animating');
        this.voiceStatusLabel.textContent = this.inCall ? 'Listening for Customer...' : 'Call Standby';
      }
    };

    this.synth.speak(utterance);
  }

  renderStateMatrix(state) {
    if (!state) return;

    let answered = 0;
    if (state.property_type) answered++;
    if (state.ownership_status) answered++;
    if (state.documents_available !== null) answered++;
    if (state.loan_amount) answered++;
    if (state.occupation && state.income_mode) answered++;
    if (state.market_value) answered++;
    if (state.tenure_years) answered++;

    this.globalChecklistCount.textContent = `${answered}/7 Criteria Captured`;

    const propStatus = state.property_type ? (state.property_type === 'Agricultural' ? 'disqualified' : 'passed') : 'pending';
    this.updateMatrixCard('property_type', propStatus, state.property_type || '—');

    const ownStatus = state.ownership_status ? 'passed' : 'pending';
    this.updateMatrixCard('ownership_status', ownStatus, state.ownership_status || '—');

    const docStatus = state.documents_available === true ? 'passed' : (state.documents_available === false ? 'disqualified' : 'pending');
    const docVal = state.documents_available === true ? 'Originals Ready (Pass)' : (state.documents_available === false ? 'No Originals / Xerox (Disqualify)' : '—');
    this.updateMatrixCard('documents_available', docStatus, docVal);

    const loanStatus = state.loan_amount ? 'passed' : 'pending';
    const loanVal = state.loan_amount ? `₹${(state.loan_amount).toLocaleString('en-IN')}` : '—';
    this.updateMatrixCard('loan_amount', loanStatus, loanVal);

    let occStatus = 'pending';
    let occVal = '—';
    if (state.occupation || state.income_mode) {
      occVal = `${state.occupation || 'Unknown'} • ${state.income_mode ? (state.income_mode === 'Bank' ? 'Bank Credit (Pass)' : 'Cash (Disqualify)') : 'Pending'}`;
      occStatus = state.income_mode === 'Cash' ? 'disqualified' : ((state.occupation && state.income_mode === 'Bank') ? 'passed' : 'pending');
    }
    this.updateMatrixCard('occupation_and_income', occStatus, occVal);

    const mvStatus = state.market_value ? 'passed' : 'pending';
    this.updateMatrixCard('market_value', mvStatus, state.market_value || '—');

    let tenStatus = 'pending';
    let tenVal = '—';
    if (state.tenure_years !== null && state.tenure_years !== undefined) {
      tenVal = `${state.tenure_years} Years`;
      tenStatus = (state.tenure_years >= 3 && state.tenure_years <= 15) ? 'passed' : 'disqualified';
    }
    this.updateMatrixCard('tenure', tenStatus, tenVal);

    this.renderDecisionHero(state);
  }

  updateMatrixCard(key, status, valText) {
    const card = document.getElementById(`card-${key}`);
    const badge = document.getElementById(`badge-${key}`);
    const val = document.getElementById(`val-${key}`);

    if (!card || !badge || !val) return;

    card.className = `matrix-card status-${status} ${key === 'tenure' ? 'span-full' : ''}`;
    badge.className = `mcard-badge badge-${status === 'passed' ? 'passed' : (status === 'disqualified' ? 'failed' : 'pending')}`;
    badge.textContent = status.toUpperCase();
    val.textContent = valText;
  }

  renderDecisionHero(state) {
    if (state.qualified) {
      this.decisionHeroCard.className = 'decision-hero-card state-qualified';
      this.decisionHeroIcon.textContent = '✅';
      this.decisionHeroTitle.textContent = 'QUALIFIED: Handoff to Senior Loan Expert';
      this.decisionHeroDesc.textContent = 'All 7 eligibility criteria met. Lead successfully qualified and forwarded for interest rate finalization.';
      this.globalStatusText.textContent = 'QUALIFIED (HANDOFF)';
      this.callLiveDot.className = 'live-dot active';
    } else if (state.disqualified) {
      this.decisionHeroCard.className = 'decision-hero-card state-disqualified';
      this.decisionHeroIcon.textContent = '⛔';
      this.decisionHeroTitle.textContent = 'DISQUALIFIED: Immediate Call Termination';
      this.decisionHeroDesc.textContent = state.disqualification_reason || 'Customer profile does not meet mandatory policy criteria.';
      this.globalStatusText.textContent = 'DISQUALIFIED';
      this.callLiveDot.className = 'live-dot disqualified';
    } else if (state.transferred) {
      this.decisionHeroCard.className = 'decision-hero-card state-transferred';
      this.decisionHeroIcon.textContent = '🔄';
      this.decisionHeroTitle.textContent = 'TRANSFERRED: Specialized Balance Transfer Team';
      this.decisionHeroDesc.textContent = 'Customer has active loan / requested lower EMI. Lead routed to Transfer Specialists.';
      this.globalStatusText.textContent = 'TRANSFERRED';
      this.callLiveDot.className = 'live-dot active';
    } else if (state.is_busy) {
      this.decisionHeroCard.className = 'decision-hero-card state-transferred';
      this.decisionHeroIcon.textContent = '⏰';
      const callbackPending = state.current_stage === 'BUSY_CALLBACK_PENDING';
      this.decisionHeroTitle.textContent = callbackPending ? 'CALLBACK TIME NEEDED' : 'CALLBACK SCHEDULED: Customer Busy';
      this.decisionHeroDesc.textContent = callbackPending
        ? 'Waiting for the customer to choose a convenient callback time.'
        : `Callback recorded for: ${state.callback_time || 'Later'}. Call politely ended.`;
      this.globalStatusText.textContent = callbackPending ? 'CALLBACK PENDING' : 'CALLBACK SET';
      this.callLiveDot.className = 'live-dot active';
    } else if (state.current_stage === 'QUALIFICATION' || state.current_stage === 'OFFER_PITCH') {
      this.decisionHeroCard.className = 'decision-hero-card state-active';
      this.decisionHeroIcon.textContent = '🎙️';
      this.decisionHeroTitle.textContent = 'Active 7-Point Qualification Dialogue';
      const firstMissing = state.missing_items && state.missing_items.length > 0 ? state.missing_items[0] : 'Processing';
      this.decisionHeroDesc.textContent = `Capturing criteria. Currently resolving: ${firstMissing.replace(/_/g, ' ')}.`;
      this.globalStatusText.textContent = 'IN QUALIFICATION';
      this.callLiveDot.className = 'live-dot active';
    } else if (this.inCall) {
      this.decisionHeroCard.className = 'decision-hero-card state-active';
      this.decisionHeroIcon.textContent = '🎙️';
      this.decisionHeroTitle.textContent = 'Call In Progress';
      this.decisionHeroDesc.textContent = 'The agent is speaking with the customer. Qualification details will appear here as they are captured.';
      this.globalStatusText.textContent = 'CALL IN PROGRESS';
      this.callLiveDot.className = 'live-dot active';
    } else {
      this.decisionHeroCard.className = 'decision-hero-card state-neutral';
      this.decisionHeroIcon.textContent = '⚡';
      this.decisionHeroTitle.textContent = 'Awaiting Outbound Call';
      this.decisionHeroDesc.textContent = 'The Voice Agent will conduct a polite 7-point qualification check and extract out-of-order details.';
      this.globalStatusText.textContent = 'STANDBY';
      this.callLiveDot.className = 'live-dot';
    }
  }

  async applyStudioConfig() {
    const configData = {
      company_name: document.getElementById('studio-cfg-company').value,
      customer_name: document.getElementById('studio-cfg-customer').value,
      agent_name: document.getElementById('studio-cfg-agent-name').value,
      agent_gender: document.getElementById('studio-cfg-agent-gender').value,
      language_to_speak: document.getElementById('studio-cfg-language').value,
      additional_context_from_rag: document.getElementById('studio-cfg-rag').value,
    };

    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configData)
      });
      const data = await res.json();
      if (configData.customer_name && configData.customer_name.trim()) {
        window.localStorage.setItem('home-credit-customer-name', configData.customer_name.trim());
      }
      this.currentLanguage = configData.language_to_speak;
      this.conversationLanguageSelect.value = this.currentLanguage;
      window.localStorage.setItem('home-credit-agent-language', this.currentLanguage);
      this.applyConversationLanguageUI();
      this.agentDisplayName.textContent = `${configData.agent_name} (AI Voice Agent)`;
      this.customerTargetDisplay.innerHTML = `Calling: <strong>${configData.customer_name}</strong> • LAP Offer (₹75L)`;
      this.agentInitialsDisplay.textContent = configData.agent_name.charAt(0);
      this.studioPromptPreview.textContent = data.rendered_prompt;
      alert('Prompt parameters updated and Jinja prompt re-rendered!');
    } catch (err) {
      console.error('Config apply error:', err);
    }
  }

  async continueWithCustomerName() {
    const customerName = this.customerNameInput.value.trim();
    if (!customerName) {
      this.customerNameError.hidden = false;
      this.customerNameInput.focus();
      return;
    }

    this.customerNameError.hidden = true;
    this.customerNameSubmit.disabled = true;
    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_name: customerName })
      });
      if (!response.ok) throw new Error('Unable to save customer name');

      const data = await response.json();
      document.getElementById('studio-cfg-customer').value = customerName;
      const resetResponse = await fetch('/api/session/reset', { method: 'POST' });
      if (!resetResponse.ok) throw new Error('Unable to reset previous session');
      const resetData = await resetResponse.json();
      this.currentState = resetData.state;
      this.renderStateMatrix(resetData.state);
      window.localStorage.setItem('home-credit-customer-name', customerName);
      if (this.customerTargetDisplay) {
        this.customerTargetDisplay.innerHTML = `Calling: <strong>${customerName}</strong> • LAP Offer (₹75L)`;
      }
      this.studioPromptPreview.textContent = data.rendered_prompt;
      this.nameGate.hidden = true;
      this.nameGate.style.display = 'none';
      window.scrollTo(0, 0);
      this.btnStartCall.focus({ preventScroll: true });
    } catch (error) {
      this.customerNameError.textContent = 'नाम सहेजा नहीं जा सका। कृपया फिर कोशिश करें।';
      this.customerNameError.hidden = false;
    } finally {
      this.customerNameSubmit.disabled = false;
    }
  }

  async loadScenariosList() {
    try {
      const res = await fetch('/api/test-scenarios/run-all');
      const data = await res.json();
      this.renderScenariosList(data.results);
    } catch (err) {
      console.error('Scenarios fetch error:', err);
      this.scenariosListContainer.innerHTML = '<div class="dialogue-bubble system"><p>Failed to load scenarios. Ensure backend is running.</p></div>';
    }
  }

  renderScenariosList(scenarios) {
    this.scenariosListContainer.innerHTML = '';
    scenarios.forEach(sc => {
      const row = document.createElement('div');
      row.className = 'scenario-item-row';
      row.innerHTML = `
        <div class="scenario-item-meta">
          <span class="scenario-tag">${sc.id}</span>
          <div class="scenario-item-name">${sc.name}</div>
          <div class="scenario-item-desc">${sc.description}</div>
        </div>
        <div class="scenario-item-actions">
          <span class="mcard-badge ${sc.passed ? 'badge-passed' : 'badge-failed'}">${sc.passed ? 'PASS' : 'FAIL'}</span>
          <button class="btn-simulate-scenario" data-id="${sc.id}">Simulate Call</button>
        </div>
      `;

      row.querySelector('button').addEventListener('click', () => this.simulateScenarioLive(sc));
      this.scenariosListContainer.appendChild(row);
    });
  }

  async simulateScenarioLive(scenario) {
    this.opsTabBtns[0].click();

    this.clearDialogueFeed();
    this.btnStartCall.disabled = true;
    this.btnEndCall.disabled = false;
    this.inCall = true;

    this.appendMessage('system', `▶️ Simulating Scenario: ${scenario.id} • ${scenario.name}`);

    for (let i = 0; i < scenario.transcript.length; i++) {
      const turn = scenario.transcript[i];
      if (turn.user && turn.user !== '[Agent Initial Call]') {
        this.appendMessage('customer', turn.user);
        await new Promise(r => setTimeout(r, 600));
      }
      this.appendMessage('agent', turn.agent);
      await new Promise(r => setTimeout(r, 700));
    }

    this.currentState = scenario.final_state;
    this.renderStateMatrix(scenario.final_state);
    this.updateTelemetryViewer();
  }

  async runAllScenariosBatch() {
    this.btnRunAllScenarios.disabled = true;
    this.btnRunAllScenarios.textContent = 'Running All 14 Scenarios...';

    try {
      const res = await fetch('/api/test-scenarios/run-all');
      const data = await res.json();
      this.renderScenariosList(data.results);
      alert(`Automated Test Suite Completed! ${data.total_passed}/${data.total_tests} Passed (${data.pass_rate}).`);
    } catch (err) {
      console.error('Batch run error:', err);
    } finally {
      this.btnRunAllScenarios.disabled = false;
      this.btnRunAllScenarios.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
        Run All 14 Test Scenarios
      `;
    }
  }

  updateTelemetryViewer() {
    if (!this.studioTelemetryJson) return;
    const telemetry = {
      timestamp: new Date().toISOString(),
      activeCall: this.inCall,
      currentState: this.currentState,
      transcript: this.conversationTranscript
    };
    this.studioTelemetryJson.textContent = JSON.stringify(telemetry, null, 2);
  }

  downloadTelemetryJSON() {
    const telemetry = {
      timestamp: new Date().toISOString(),
      currentState: this.currentState,
      transcript: this.conversationTranscript
    };
    const blob = new Blob([JSON.stringify(telemetry, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `home_credit_telemetry_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  downloadTranscriptTXT() {
    let txt = `======================================================================\n`;
    txt += `HOME CREDIT - LOAN AGAINST PROPERTY (LAP) AI VOICE AGENT TRANSCRIPT\n`;
    txt += `Timestamp: ${new Date().toLocaleString()}\n`;
    txt += `======================================================================\n\n`;

    this.conversationTranscript.forEach(t => {
      txt += `[${t.time}] ${t.speaker.toUpperCase()}: ${t.text}\n\n`;
    });

    if (this.currentState) {
      txt += `\n----------------- FINAL QUALIFICATION STATE -----------------\n`;
      txt += `Stage: ${this.currentState.current_stage}\n`;
      txt += `Qualified: ${this.currentState.qualified}\n`;
      txt += `Disqualified: ${this.currentState.disqualified} (${this.currentState.disqualification_reason || 'N/A'})\n`;
      txt += `Transferred: ${this.currentState.transferred} (${this.currentState.transfer_reason || 'N/A'})\n`;
      txt += `Property Type: ${this.currentState.property_type}\n`;
      txt += `Ownership: ${this.currentState.ownership_status}\n`;
      txt += `Original Docs: ${this.currentState.documents_available}\n`;
      txt += `Loan Amount: ₹${this.currentState.loan_amount || 'N/A'}\n`;
      txt += `Occupation/Income: ${this.currentState.occupation} / ${this.currentState.income_mode}\n`;
      txt += `Market Value: ${this.currentState.market_value}\n`;
      txt += `Tenure: ${this.currentState.tenure_years} Years\n`;
      txt += `======================================================================\n`;
    }

    const blob = new Blob([txt], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `home_credit_transcript_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  copyRetellConfig() {
    const config = {
      agent_name: "Home Credit LAP Qualifier",
      voice_id: "11labs-Adrian",
      llm_model: "gpt-4o",
      general_prompt: this.studioPromptPreview.textContent
    };
    navigator.clipboard.writeText(JSON.stringify(config, null, 2));
    alert('Retell AI configuration copied to clipboard!');
  }

  copyBolnaConfig() {
    const config = {
      agent_name: "Home Credit LAP Qualifier",
      system_prompt: this.studioPromptPreview.textContent
    };
    navigator.clipboard.writeText(JSON.stringify(config, null, 2));
    alert('Bolna configuration copied to clipboard!');
  }

  copyPromptText() {
    navigator.clipboard.writeText(this.studioPromptPreview.textContent);
    alert('Master System Prompt copied to clipboard!');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.studio = new VoiceAgentStudio();
});
