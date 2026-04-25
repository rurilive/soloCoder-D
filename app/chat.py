from flask_socketio import emit, join_room, leave_room
from flask import request
from app import socketio
from app.database import User, Conversation, Message
import uuid

visitor_sessions = {}
agent_sessions = {}

EMOJIS = [
    '😀', '😂', '🥰', '😎', '🤔', '👍', '👎', '❤️',
    '🔥', '🎉', '😢', '😡', '🙏', '👋', '✨', '💯'
]

def get_available_agent():
    if agent_sessions:
        for agent_id, session_data in agent_sessions.items():
            return agent_id
    return None

@socketio.on('visitor_connect')
def handle_visitor_connect(data):
    visitor_id = data.get('visitor_id') or str(uuid.uuid4())
    visitor_name = data.get('visitor_name', f'访客_{visitor_id[:8]}')
    
    user = User.get(visitor_id)
    if not user:
        user = User.create(visitor_id, visitor_name, 'visitor')
    else:
        user.update_last_active()
    
    visitor_sessions[request.sid] = {
        'visitor_id': visitor_id,
        'visitor_name': visitor_name,
        'conversation_id': None
    }
    
    conversation = Conversation.get_by_visitor(visitor_id)
    if not conversation:
        conversation = Conversation.create(visitor_id)
    
    visitor_sessions[request.sid]['conversation_id'] = conversation.conversation_id
    join_room(conversation.conversation_id)
    
    emit('visitor_connected', {
        'visitor_id': visitor_id,
        'conversation_id': conversation.conversation_id,
        'status': conversation.status
    })
    
    available_agent = get_available_agent()
    if available_agent and conversation.status == 'waiting':
        conversation.assign_agent(available_agent)
        
        agent_sid = None
        for sid, data in agent_sessions.items():
            if data.get('agent_id') == available_agent:
                agent_sid = sid
                break
        
        if agent_sid:
            socketio.server.enter_room(agent_sid, conversation.conversation_id)
            socketio.emit('new_conversation', {
                'conversation_id': conversation.conversation_id,
                'visitor_id': visitor_id,
                'visitor_name': visitor_name
            }, room=agent_sid)
        
        emit('agent_assigned', {
            'agent_id': available_agent,
            'conversation_id': conversation.conversation_id
        }, room=conversation.conversation_id)
    
    if agent_sessions:
        for sid in agent_sessions.keys():
            socketio.emit('update_waiting_list', {
                'count': len(Conversation.get_waiting())
            }, room=sid)

@socketio.on('agent_connect')
def handle_agent_connect(data):
    agent_id = data.get('agent_id') or str(uuid.uuid4())
    agent_name = data.get('agent_name', f'客服_{agent_id[:8]}')
    
    user = User.get(agent_id)
    if not user:
        user = User.create(agent_id, agent_name, 'agent')
    else:
        user.update_last_active()
    
    agent_sessions[request.sid] = {
        'agent_id': agent_id,
        'agent_name': agent_name
    }
    
    conversations = Conversation.get_active_for_agent(agent_id)
    
    emit('agent_connected', {
        'agent_id': agent_id,
        'active_conversations': [
            {
                'conversation_id': c.conversation_id,
                'visitor_id': c.visitor_id,
                'status': c.status
            } for c in conversations
        ]
    })
    
    waiting = Conversation.get_waiting()
    if waiting:
        conversation = waiting[0]
        conversation.assign_agent(agent_id)
        
        join_room(conversation.conversation_id)
        
        emit('agent_assigned', {
            'agent_id': agent_id,
            'agent_name': agent_name,
            'conversation_id': conversation.conversation_id
        }, room=conversation.conversation_id)
    
    emit('update_waiting_list', {
        'count': len(Conversation.get_waiting())
    })

@socketio.on('send_message')
def handle_send_message(data):
    conversation_id = data.get('conversation_id')
    content = data.get('content', '')
    message_type = data.get('message_type', 'text')
    file_name = data.get('file_name')
    file_path = data.get('file_path')
    file_size = data.get('file_size')
    
    sender_id = None
    sender_type = None
    
    if request.sid in visitor_sessions:
        visitor_data = visitor_sessions[request.sid]
        sender_id = visitor_data['visitor_id']
        sender_type = 'visitor'
        if not conversation_id:
            conversation_id = visitor_data.get('conversation_id')
    elif request.sid in agent_sessions:
        agent_data = agent_sessions[request.sid]
        sender_id = agent_data['agent_id']
        sender_type = 'agent'
    
    if not all([conversation_id, sender_id, content]):
        return
    
    conversation = Conversation.get(conversation_id)
    if not conversation:
        return
    
    if message_type == 'emoji':
        if content in EMOJIS:
            pass
    
    message = Message.create(
        conversation_id=conversation_id,
        sender_id=sender_id,
        sender_type=sender_type,
        content=content,
        message_type=message_type,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size
    )
    
    emit('new_message', {
        'conversation_id': conversation_id,
        'sender_id': sender_id,
        'sender_type': sender_type,
        'content': content,
        'message_type': message_type,
        'file_name': file_name,
        'file_size': file_size,
        'created_at': message.created_at
    }, room=conversation_id)

@socketio.on('get_history')
def handle_get_history(data):
    conversation_id = data.get('conversation_id')
    limit = data.get('limit', 100)
    
    if not conversation_id:
        if request.sid in visitor_sessions:
            conversation_id = visitor_sessions[request.sid].get('conversation_id')
    
    if not conversation_id:
        return
    
    messages = Message.get_by_conversation(conversation_id, limit)
    
    emit('history_messages', {
        'conversation_id': conversation_id,
        'messages': [m.to_dict() for m in messages]
    })

@socketio.on('join_conversation')
def handle_join_conversation(data):
    conversation_id = data.get('conversation_id')
    agent_id = None
    
    if request.sid in agent_sessions:
        agent_id = agent_sessions[request.sid]['agent_id']
    
    if not conversation_id or not agent_id:
        return
    
    conversation = Conversation.get(conversation_id)
    if not conversation:
        return
    
    if conversation.status == 'waiting':
        conversation.assign_agent(agent_id)
        
        for sid, data in visitor_sessions.items():
            if data.get('conversation_id') == conversation_id:
                socketio.emit('agent_assigned', {
                    'agent_id': agent_id,
                    'agent_name': agent_sessions[request.sid]['agent_name'],
                    'conversation_id': conversation_id
                }, room=sid)
                break
    
    join_room(conversation_id)
    
    messages = Message.get_by_conversation(conversation_id)
    
    emit('conversation_joined', {
        'conversation_id': conversation_id,
        'visitor_id': conversation.visitor_id,
        'status': conversation.status,
        'messages': [m.to_dict() for m in messages]
    })

@socketio.on('leave_conversation')
def handle_leave_conversation(data):
    conversation_id = data.get('conversation_id')
    if conversation_id:
        leave_room(conversation_id)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in visitor_sessions:
        del visitor_sessions[request.sid]
    
    if request.sid in agent_sessions:
        del agent_sessions[request.sid]
        
        for sid in agent_sessions.keys():
            socketio.emit('update_waiting_list', {
                'count': len(Conversation.get_waiting())
            }, room=sid)
