"""
Intelligent Support Assistant for Mantis
Provides real-time support capabilities integrated into the AI assistant
"""

import streamlit as st
from typing import Dict, List, Any, Optional
import json
import re
from datetime import datetime

class IntelligentSupportAssistant:
    """
    Enhanced AI assistant with support capabilities
    Integrates trained ML models for intelligent support responses
    """
    
    def __init__(self):
        self.support_triggers = self._initialize_support_triggers()
        self.quick_help_commands = self._initialize_quick_help()
        self.context_awareness = {}
        
    def _initialize_support_triggers(self) -> Dict[str, List[str]]:
        """Initialize trigger words/phrases that indicate support requests"""
        return {
            "process_help": [
                "how do i", "how to", "steps to", "process to", "way to",
                "create", "build", "generate", "make", "set up", "configure"
            ],
            "troubleshooting": [
                "error", "problem", "issue", "not working", "broken", "failed",
                "can't", "unable to", "doesn't work", "won't load", "stuck"
            ],
            "feature_explanation": [
                "what is", "what does", "explain", "tell me about", "how does",
                "what can", "capabilities", "features", "functions"
            ],
            "navigation_help": [
                "where is", "where can i find", "how to get to", "navigate to",
                "location of", "find the", "access"
            ]
        }
    
    def _initialize_quick_help(self) -> Dict[str, Dict[str, Any]]:
        """Initialize quick help responses for common queries"""
        return {
            "modules": {
                "response": """
                **GovSight has 3 main modules:**
                
                🧭 **Navi** - Navigation & Planning Hub
                - Scenario Planning & What-if Analysis
                - BI Sandbox for Data Visualization
                - Custom Chart Builder
                - Monte Carlo Risk Simulation
                
                🦂 **Mantis** - AI Intelligence Hub  
                - Conversational AI Assistant (that's me!)
                - Grant Opportunity Intelligence
                - Document Analysis & Processing
                - Strategic Recommendations
                
                🏛️ **Vatica** - Document & Collaboration Hub
                - Document Management & Annotation
                - Collaborative Review Workflows
                - Version Control & Export
                """,
                "quick_actions": ["Show Navi features", "Show Mantis features", "Show Vatica features"]
            },
            "charts": {
                "response": """
                **Available Chart Types in Custom Visualization Builder:**
                
                📊 **Basic Charts:** Bar, Line, Scatter, Area, Pie
                📈 **Statistical:** Box Plot, Violin Plot, Histogram  
                🔥 **Advanced:** Heatmap, Treemap, Waterfall, Funnel
                📍 **Specialized:** Geographic Maps, Network Graphs
                
                **To create charts:**
                1. Go to Navi → Custom Visualizations
                2. Select chart type and data columns
                3. Customize styling and colors
                4. Generate and export your chart
                """,
                "quick_actions": ["Open Chart Builder", "Show Chart Examples", "Export Options Help"]
            },
            "budget_scenario": {
                "response": """
                **Creating Budget Scenarios - Step by Step:**
                
                1. **Access:** Go to Navi → Scenario Planner
                2. **Setup:** Select your organization from dropdown
                3. **Type:** Choose scenario type (Budget/Revenue/Mixed)
                4. **Parameters:** Input your scenario variables
                5. **Funding:** Configure funding sources and allocations
                6. **Analysis:** Run the scenario analysis
                7. **Review:** Examine results and AI recommendations
                8. **Export:** Generate professional scenario report
                
                **Pro Tips:**
                - Use multiple scenarios to compare options
                - Include risk factors in your analysis
                - Export scenarios for stakeholder presentations
                """,
                "quick_actions": ["Open Scenario Planner", "Show Example Scenario", "Export Templates"]
            },
            "grants": {
                "response": """
                **Finding Grant Opportunities:**
                
                🎯 **Grant Intelligence Features:**
                - Search across FEMA, DOT, EPA, HUD, USDA, DOJ
                - AI-powered matching to your needs
                - Eligibility analysis and recommendations
                - Application deadline tracking
                
                **How to Use:**
                1. Stay in Mantis (AI Intelligence Hub)
                2. Ask me: "Find grants for [your project type]"
                3. I'll search and analyze opportunities
                4. Get detailed eligibility and application guidance
                
                **Supported Grant Types:**
                - Infrastructure & Transportation
                - Environmental & Sustainability  
                - Public Safety & Emergency Management
                - Housing & Community Development
                - Agriculture & Rural Development
                """,
                "quick_actions": ["Search Infrastructure Grants", "Find Emergency Grants", "Show All Grant Sources"]
            },
            "data_issues": {
                "response": """
                **Troubleshooting Data Loading Issues:**
                
                🔍 **Check These First:**
                1. **Organization Selection:** Verify correct org in dropdown
                2. **Data Permissions:** Ensure you have access rights
                3. **Database Connection:** Check if other modules load data
                4. **Browser Refresh:** Try refreshing the page
                
                🛠️ **Common Solutions:**
                - Switch organizations and switch back
                - Clear browser cache and reload
                - Check with administrator for data access
                - Try a different browser or incognito mode
                
                📞 **Still Having Issues?**
                - Contact your system administrator
                - Check the Admin Panel for data status
                - Try accessing during off-peak hours
                """,
                "quick_actions": ["Check Data Status", "Test Database Connection", "Contact Admin"]
            }
        }
    
    def detect_support_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Detect if user message is a support request and classify the intent
        
        Args:
            user_message (str): The user's message
            
        Returns:
            Dict containing intent classification and confidence
        """
        message_lower = user_message.lower()
        detected_intents = {}
        
        # Check for support trigger words
        for intent_type, triggers in self.support_triggers.items():
            score = 0
            matched_triggers = []
            
            for trigger in triggers:
                if trigger in message_lower:
                    score += 1
                    matched_triggers.append(trigger)
            
            if score > 0:
                detected_intents[intent_type] = {
                    "score": score,
                    "triggers": matched_triggers,
                    "confidence": min(score / len(triggers), 1.0)
                }
        
        # Determine primary intent
        if detected_intents:
            primary_intent = max(detected_intents.keys(), 
                               key=lambda x: detected_intents[x]["score"])
            
            return {
                "is_support_request": True,
                "primary_intent": primary_intent,
                "all_intents": detected_intents,
                "confidence": detected_intents[primary_intent]["confidence"]
            }
        
        return {
            "is_support_request": False,
            "primary_intent": None,
            "all_intents": {},
            "confidence": 0.0
        }
    
    def generate_support_response(self, user_message: str, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate intelligent support response based on intent analysis
        
        Args:
            user_message (str): User's original message
            intent_analysis (Dict): Intent classification results
            
        Returns:
            Dict containing structured support response
        """
        if not intent_analysis["is_support_request"]:
            return None
        
        primary_intent = intent_analysis["primary_intent"]
        message_lower = user_message.lower()
        
        # Check for specific quick help topics
        for topic, help_info in self.quick_help_commands.items():
            topic_keywords = self._get_topic_keywords(topic)
            if any(keyword in message_lower for keyword in topic_keywords):
                return {
                    "type": "quick_help",
                    "topic": topic,
                    "response": help_info["response"],
                    "quick_actions": help_info["quick_actions"],
                    "confidence": intent_analysis["confidence"]
                }
        
        # Generate contextual support response based on intent
        if primary_intent == "process_help":
            return self._generate_process_help(user_message)
        elif primary_intent == "troubleshooting":
            return self._generate_troubleshooting_help(user_message)
        elif primary_intent == "feature_explanation":
            return self._generate_feature_explanation(user_message)
        elif primary_intent == "navigation_help":
            return self._generate_navigation_help(user_message)
        
        # Fallback response
        return {
            "type": "general_support",
            "response": """
            I'm here to help you with GovSight! I can assist you with:
            
            📋 **Process Help:** Creating scenarios, building charts, using features
            🔧 **Troubleshooting:** Fixing errors, data issues, performance problems  
            💡 **Feature Explanations:** Understanding modules, capabilities, functions
            🧭 **Navigation:** Finding features, accessing tools, getting around
            
            Try asking me:
            - "How do I create a budget scenario?"
            - "Why isn't my data loading?"
            - "What charts can I create?"
            - "Where is the grant search?"
            """,
            "quick_actions": [
                "Show all modules",
                "Common troubleshooting", 
                "Feature overview",
                "Getting started guide"
            ],
            "confidence": intent_analysis["confidence"]
        }
    
    def _get_topic_keywords(self, topic: str) -> List[str]:
        """Get relevant keywords for quick help topics"""
        topic_keywords = {
            "modules": ["module", "modules", "section", "sections", "navi", "mantis", "vatica"],
            "charts": ["chart", "charts", "visualization", "graph", "plot", "visual"],
            "budget_scenario": ["scenario", "budget", "planning", "forecast", "what-if"],
            "grants": ["grant", "grants", "funding", "opportunity", "opportunities"],
            "data_issues": ["data", "loading", "not loading", "empty", "missing"]
        }
        return topic_keywords.get(topic, [])
    
    def _generate_process_help(self, user_message: str) -> Dict[str, Any]:
        """Generate process-specific help response"""
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["scenario", "budget", "planning"]):
            return {
                "type": "process_help",
                "topic": "budget_scenario",
                "response": self.quick_help_commands["budget_scenario"]["response"],
                "quick_actions": self.quick_help_commands["budget_scenario"]["quick_actions"]
            }
        elif any(word in message_lower for word in ["chart", "visualization", "graph"]):
            return {
                "type": "process_help", 
                "topic": "charts",
                "response": self.quick_help_commands["charts"]["response"],
                "quick_actions": self.quick_help_commands["charts"]["quick_actions"]
            }
        elif any(word in message_lower for word in ["grant", "funding"]):
            return {
                "type": "process_help",
                "topic": "grants", 
                "response": self.quick_help_commands["grants"]["response"],
                "quick_actions": self.quick_help_commands["grants"]["quick_actions"]
            }
        
        return {
            "type": "process_help",
            "response": """
            I can guide you through these key processes:
            
            🎯 **Budget Scenario Planning** - Create and analyze funding scenarios
            📊 **Custom Visualization** - Build interactive charts and dashboards  
            💰 **Grant Research** - Find and analyze funding opportunities
            📄 **Document Analysis** - Process and extract insights from documents
            📋 **Report Generation** - Create professional reports and summaries
            
            What specific process would you like help with?
            """,
            "quick_actions": ["Budget Scenarios", "Chart Building", "Grant Search", "Document Upload"]
        }
    
    def _generate_troubleshooting_help(self, user_message: str) -> Dict[str, Any]:
        """Generate troubleshooting-specific help response"""
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["data", "loading", "empty", "not showing"]):
            return {
                "type": "troubleshooting",
                "topic": "data_issues",
                "response": self.quick_help_commands["data_issues"]["response"],
                "quick_actions": self.quick_help_commands["data_issues"]["quick_actions"]
            }
        
        return {
            "type": "troubleshooting",
            "response": """
            **Common Troubleshooting Steps:**
            
            🔄 **First, Try These:**
            1. Refresh the page (F5 or Ctrl+R)
            2. Check your organization selection
            3. Clear browser cache and cookies
            4. Try incognito/private browsing mode
            
            📊 **Data Issues:**
            - Verify organization dropdown selection
            - Check data permissions with admin
            - Try switching organizations and back
            
            🎨 **Visualization Problems:**
            - Ensure sufficient data for chart type
            - Check column data types match chart requirements
            - Try a different chart type
            
            🐌 **Performance Issues:**
            - Apply filters to reduce data size
            - Use smaller date ranges
            - Check internet connection speed
            
            What specific issue are you experiencing?
            """,
            "quick_actions": ["Check Data Status", "Performance Tips", "Contact Support", "System Status"]
        }
    
    def _generate_feature_explanation(self, user_message: str) -> Dict[str, Any]:
        """Generate feature explanation response"""
        return {
            "type": "feature_explanation",
            "response": self.quick_help_commands["modules"]["response"],
            "quick_actions": self.quick_help_commands["modules"]["quick_actions"]
        }
    
    def _generate_navigation_help(self, user_message: str) -> Dict[str, Any]:
        """Generate navigation help response"""
        return {
            "type": "navigation_help",
            "response": """
            **GovSight Navigation Guide:**
            
            🏠 **Main Dashboard:** Click GovSight logo to return home
            
            🧭 **Navi Module:** Planning & Analysis
            - Scenario Planner: Budget modeling and what-if analysis
            - BI Sandbox: Data exploration and analytics
            - Custom Visualizations: Interactive chart builder
            - Monte Carlo: Risk simulation and forecasting
            
            🦂 **Mantis Module:** AI Intelligence
            - AI Assistant: This conversational interface
            - Grant Intelligence: Funding opportunity search
            - Document Analysis: Upload and analyze files
            - Support Training: AI knowledge management
            
            🏛️ **Vatica Module:** Document Management
            - Document Library: File storage and organization
            - Annotation Tools: Collaborative document review
            - Version Control: Track document changes
            
            Where would you like to go?
            """,
            "quick_actions": ["Go to Navi", "Go to Mantis", "Go to Vatica", "Back to Dashboard"]
        }

def integrate_support_with_mantis_chat():
    """
    Integration function to enhance Mantis chat with support capabilities
    This should be called from the main Mantis chat interface
    """
    
    # Initialize support assistant if not already done
    if 'mantis_support_assistant' not in st.session_state:
        st.session_state.mantis_support_assistant = IntelligentSupportAssistant()
    
    support_assistant = st.session_state.mantis_support_assistant
    
    return support_assistant

def render_support_response(support_response: Dict[str, Any]):
    """
    Render a structured support response in the Mantis chat interface
    
    Args:
        support_response (Dict): Support response data from the assistant
    """
    
    if not support_response:
        return
    
    # Render the main response
    st.markdown("### 🎯 Support Response")
    st.markdown(support_response["response"])
    
    # Render quick actions if available
    if "quick_actions" in support_response and support_response["quick_actions"]:
        st.markdown("#### Quick Actions:")
        
        cols = st.columns(min(len(support_response["quick_actions"]), 4))
        for i, action in enumerate(support_response["quick_actions"]):
            with cols[i % len(cols)]:
                if st.button(action, key=f"support_action_{i}"):
                    st.info(f"Action selected: {action}")
                    # Here you could implement actual navigation or actions
    
    # Show confidence if available
    if "confidence" in support_response:
        confidence = support_response["confidence"]
        if confidence < 0.5:
            st.info("💡 If this doesn't answer your question, try being more specific or contact support.")