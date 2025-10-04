#!/usr/bin/env python3
"""
Simple AutoGen Studio-like Demo
This script provides a basic demonstration of AutoGen functionality
without requiring the full AutoGen Studio installation.
"""

import os
import json
from typing import List, Dict, Any

def print_header():
    """Print a welcome header"""
    print("=" * 60)
    print("         🤖 AUTOGEN DEMO - MULTI-AGENT SYSTEM 🤖")
    print("=" * 60)
    print()

def print_separator():
    """Print a section separator"""
    print("-" * 60)

def display_agents():
    """Display available agent configurations"""
    print("📋 AVAILABLE AGENT TEAMS:")
    print()
    print("1. 🧮 Calculator Agent Team")
    print("   - Single assistant agent with calculator tool")
    print("   - Can perform basic arithmetic operations")
    print()
    print("2. ✈️ Travel Planning Team") 
    print("   - Multi-agent travel planning system")
    print("   - Planner, Local Expert, Language Expert, Summary Agent")
    print()
    print("3. 💬 Custom Chat")
    print("   - Simple two-agent conversation")
    print()

def display_agent_config(config_name: str):
    """Display agent configuration details"""
    configs = {
        "calculator": {
            "name": "Calculator Team",
            "description": "A single assistant agent with calculator capabilities",
            "agents": ["Assistant Agent with Calculator Tool"],
            "tools": ["Basic Calculator (+, -, *, /)"],
            "use_case": "Mathematical computations and calculations"
        },
        "travel": {
            "name": "Travel Planning Team", 
            "description": "Multi-agent team for comprehensive travel planning",
            "agents": [
                "Planner Agent - Creates initial travel plans",
                "Local Agent - Suggests local activities and places", 
                "Language Agent - Provides language and communication tips",
                "Summary Agent - Creates final integrated travel plan"
            ],
            "tools": ["None (LLM-based reasoning only)"],
            "use_case": "End-to-end travel itinerary planning"
        },
        "chat": {
            "name": "Simple Chat",
            "description": "Basic conversational agents",
            "agents": ["User Assistant", "Helper Agent"],
            "tools": ["None"],
            "use_case": "General conversation and assistance"
        }
    }
    
    if config_name in configs:
        config = configs[config_name]
        print(f"🎯 TEAM: {config['name']}")
        print(f"📝 Description: {config['description']}")
        print(f"👥 Agents:")
        for agent in config['agents']:
            print(f"   • {agent}")
        print(f"🔧 Tools: {', '.join(config['tools'])}")
        print(f"💡 Use Case: {config['use_case']}")
    else:
        print("❌ Configuration not found")

def simulate_agent_interaction(team_type: str, task: str):
    """Simulate agent interactions for demo purposes"""
    print(f"🚀 STARTING {team_type.upper()} TEAM...")
    print(f"📝 Task: {task}")
    print()
    
    if team_type == "calculator":
        simulate_calculator_team(task)
    elif team_type == "travel":
        simulate_travel_team(task)
    elif team_type == "chat":
        simulate_chat_team(task)

def simulate_calculator_team(task: str):
    """Simulate calculator agent interaction"""
    print("🤖 Assistant Agent: I'll help you with your calculation.")
    print("🔧 Using calculator tool...")
    
    # Simple calculation simulation
    if "2+3" in task or "2 + 3" in task:
        print("🧮 Calculator Tool: Performing addition: 2 + 3")
        print("✅ Result: 5")
    elif "10*5" in task or "10 * 5" in task:
        print("🧮 Calculator Tool: Performing multiplication: 10 * 5") 
        print("✅ Result: 50")
    else:
        print("🧮 Calculator Tool: Processing calculation...")
        print("✅ Result: [Calculation would be performed here]")
    
    print("🤖 Assistant Agent: The calculation is complete. TERMINATE")

def simulate_travel_team(task: str):
    """Simulate travel planning team interaction"""
    print("🗺️ Planner Agent: I'll create an initial travel plan for your trip.")
    print("   Creating a 3-day itinerary with key attractions and activities.")
    print()
    
    print("🏛️ Local Agent: Let me add some authentic local experiences!")
    print("   I recommend visiting local markets, trying street food, and cultural sites.")
    print()
    
    print("🗣️ Language Agent: Here are important language tips for your destination.")
    print("   Learn basic greetings, useful phrases, and download a translation app.")
    print()
    
    print("📋 Summary Agent: Creating comprehensive travel plan...")
    print("   ✈️ Day 1: Arrival, city orientation, main attractions")
    print("   🌅 Day 2: Cultural experiences, local cuisine, markets")
    print("   🎒 Day 3: Adventure activities, shopping, departure prep")
    print("   📱 Language prep: Key phrases, translation apps")
    print("   🚀 Your complete travel plan is ready! TERMINATE")

def simulate_chat_team(task: str):
    """Simulate simple chat interaction"""
    print("👋 User Assistant: Hello! I'm here to help with your request.")
    print("🤝 Helper Agent: I'll provide additional support and insights.")
    print("💬 User Assistant: Let me address your question step by step.")
    print("✨ Helper Agent: I can offer alternative perspectives if needed.")
    print("✅ User Assistant: I believe we've addressed your request. TERMINATE")

def interactive_demo():
    """Run interactive demo"""
    print_header()
    
    while True:
        display_agents()
        print_separator()
        
        choice = input("Select a team (1-3) or 'q' to quit: ").strip()
        
        if choice.lower() == 'q':
            print("👋 Thanks for trying the AutoGen Demo!")
            break
            
        team_map = {"1": "calculator", "2": "travel", "3": "chat"}
        
        if choice not in team_map:
            print("❌ Invalid choice. Please try again.\n")
            continue
            
        team_type = team_map[choice]
        print_separator()
        display_agent_config(team_type)
        print_separator()
        
        # Get task from user
        if team_type == "calculator":
            task = input("Enter a calculation (e.g., '2+3' or '10*5'): ").strip()
        elif team_type == "travel":
            task = input("Enter destination (e.g., 'Plan a 3 day trip to Nepal'): ").strip()
        else:
            task = input("Enter your question or request: ").strip()
            
        if not task:
            task = "Default task for demonstration"
            
        print_separator()
        simulate_agent_interaction(team_type, task)
        print_separator()
        
        input("\nPress Enter to continue...")
        print("\n" + "=" * 60 + "\n")

def display_real_configs():
    """Display information about real AutoGen Studio configs"""
    print("📁 REAL AUTOGEN STUDIO CONFIGURATIONS:")
    print()
    print("This demo is based on actual AutoGen Studio team configurations:")
    print("• team.json - Calculator agent with function tools")  
    print("• travel_team.json - Multi-agent travel planning team")
    print()
    print("These configs use:")
    print("• autogen_agentchat.agents.AssistantAgent")
    print("• autogen_agentchat.teams.RoundRobinGroupChat") 
    print("• autogen_ext.models.openai.OpenAIChatCompletionClient")
    print("• Custom function tools and termination conditions")
    print()

def main():
    """Main function"""
    print("AutoGen Studio Demo - Choose an option:")
    print("1. Interactive Demo")
    print("2. View Real AutoGen Configs") 
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        interactive_demo()
    elif choice == "2":
        display_real_configs()
        input("\nPress Enter to continue...")
        main()
    elif choice == "3":
        print("Goodbye!")
    else:
        print("Invalid choice, please try again.")
        main()

if __name__ == "__main__":
    main()