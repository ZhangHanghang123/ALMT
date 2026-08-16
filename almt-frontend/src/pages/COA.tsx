import { useState, useEffect } from 'react'
import { Tree, Button, Space, Modal, Form, Input, message, Popconfirm, Card, Row, Col } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, FolderOutlined } from '@ant-design/icons'
import apiClient from '../api/client'

interface TreeNode {
  id: number
  uuid: string
  coa_cd: string
  coa_name: string | null
  leaf_flag: string | null
  title: string
  key: string
  children?: TreeNode[]
}

const COAPage = () => {
  const [treeData, setTreeData] = useState<TreeNode[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedKeys, setExpandedKeys] = useState<string[]>([])
  const [selectedKey, setSelectedKey] = useState<string>('')
  const [modalVisible, setModalVisible] = useState(false)
  const [editingItem, setEditingItem] = useState<any>(null)
  const [form] = Form.useForm()

  const fetchTree = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/coa/tree')
      console.log('COA tree data:', res.data)
      const data = Array.isArray(res.data) ? res.data : []
      setTreeData(data)

      const keys: string[] = []
      const expand = (nodes: TreeNode[], level: number) => {
        if (level > 3) return
        nodes.forEach(n => {
          keys.push(n.key)
          if (n.children && n.children.length > 0) expand(n.children, level + 1)
        })
      }
      expand(data, 0)
      setExpandedKeys(keys)
      message.success(`加载成功，共 ${data.length} 个根节点`)
    } catch (e: any) {
      console.error('加载COA失败:', e)
      message.error('加载失败: ' + (e.message || e.response?.data?.detail || ''))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchTree() }, [])

  const findNode = (nodes: TreeNode[], key: string): any => {
    for (const n of nodes) {
      if (n.key === key) return n
      if (n.children) {
        const found = findNode(n.children, key)
        if (found) return found
      }
    }
    return null
  }

  const handleAdd = () => {
    if (!selectedKey) {
      message.warning('请先选择父级账户册')
      return
    }
    setEditingItem(null)
    form.resetFields()
    const parentNode = findNode(treeData, selectedKey)
    form.setFieldsValue({ parent_coa_cd: parentNode?.coa_cd || '' })
    setModalVisible(true)
  }

  const handleEdit = () => {
    if (!selectedKey) {
      message.warning('请先选择要编辑的账户册')
      return
    }
    const node = findNode(treeData, selectedKey)
    if (node) {
      setEditingItem(node)
      form.setFieldsValue({
        parent_coa_cd: '',
        coa_cd: node.coa_cd,
        coa_name: node.coa_name || ''
      })
      setModalVisible(true)
    }
  }

  const handleDelete = async () => {
    if (!selectedKey) {
      message.warning('请先选择要删除的账户册')
      return
    }
    try {
      await apiClient.delete(`/coa/${selectedKey}`)
      message.success('删除成功')
      setSelectedKey('')
      fetchTree()
    } catch (e: any) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingItem) {
        await apiClient.put(`/coa/${editingItem.id}`, values)
        message.success('更新成功')
      } else {
        await apiClient.post('/coa', { ...values, leaf_flag: '0' })
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchTree()
    } catch (e: any) {
      message.error('操作失败: ' + (e.response?.data?.detail || e.message || ''))
    }
  }

  const renderTreeNodes = (nodes: TreeNode[]): any[] => {
    return nodes.map(node => ({
      id: node.id,
      uuid: node.uuid,
      coa_cd: node.coa_cd,
      coa_name: node.coa_name,
      leaf_flag: node.leaf_flag,
      title: `${node.coa_cd}${node.coa_name ? ' - ' + node.coa_name : ''}`,
      key: node.key,
      icon: <FolderOutlined />,
      children: node.children && node.children.length > 0 ? renderTreeNodes(node.children) : undefined
    }))
  }

  const selectedNode = findNode(treeData, selectedKey)

  return (
    <div>
      <Row gutter={16}>
        <Col span={16}>
          <Card
            title={`账户册树形结构 (${treeData.length} 个根节点)`}
            extra={
              <Space>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新增</Button>
                <Button icon={<EditOutlined />} onClick={handleEdit} disabled={!selectedKey}>编辑</Button>
                <Popconfirm title="确认删除?" onConfirm={handleDelete}>
                  <Button danger icon={<DeleteOutlined />} disabled={!selectedKey}>删除</Button>
                </Popconfirm>
                <Button onClick={fetchTree}>刷新</Button>
              </Space>
            }
          >
            {treeData.length === 0 && !loading && (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                暂无数据，请点击"刷新"按钮或检查网络
              </div>
            )}
            <Tree
              treeData={renderTreeNodes(treeData)}
              expandedKeys={expandedKeys}
              onExpand={(keys) => setExpandedKeys(keys as string[])}
              selectedKeys={selectedKey ? [selectedKey] : []}
              onSelect={(keys) => setSelectedKey((keys[0] as string) || '')}
              showLine
              showIcon
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="账户册详情">
            {selectedNode ? (
              <div>
                <p><strong>编码:</strong> {selectedNode.coa_cd}</p>
                <p><strong>名称:</strong> {selectedNode.coa_name || '-'}</p>
                <p><strong>叶子节点:</strong> {selectedNode.leaf_flag === '1' ? '是' : '否'}</p>
                <p><strong>子节点数:</strong> {selectedNode.children?.length || 0}</p>
                <p><strong>UUID:</strong> {selectedNode.uuid}</p>
              </div>
            ) : (
              <p style={{ color: '#999' }}>请选择账户册</p>
            )}
          </Card>
        </Col>
      </Row>

      <Modal title={editingItem ? '编辑账户册' : '新增账户册'} open={modalVisible} onOk={handleSubmit} onCancel={() => setModalVisible(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="parent_coa_cd" label="父级编码">
            <Input disabled />
          </Form.Item>
          <Form.Item name="coa_cd" label="账户册编码" rules={[{ required: true }]}>
            <Input disabled={!!editingItem} />
          </Form.Item>
          <Form.Item name="coa_name" label="账户册名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default COAPage
